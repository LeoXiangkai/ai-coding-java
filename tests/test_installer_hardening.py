from __future__ import annotations

import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import AICJ, FIXTURE, REPO, files_under, run_aicj, snapshot

sys.path.insert(0, str(REPO / "installer"))
from lib import util  # noqa: E402

BEGIN = "<!-- aicj:begin -->"
END = "<!-- aicj:end -->"


def manifest_of(home: Path) -> dict:
    return json.loads((home / ".claude/aicj/manifest.json").read_text(encoding="utf-8"))


def entry_of(home: Path, rel: str) -> dict:
    return next(e for e in manifest_of(home)["entries"] if e["path"] == rel)


def fixture_copy(tmp_path: Path) -> Path:
    dest = tmp_path / "component"
    shutil.copytree(FIXTURE, dest)
    return dest


def edit_json(path: Path, mutate) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def ok(result: subprocess.CompletedProcess) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr


def refused(result: subprocess.CompletedProcess) -> None:
    assert result.returncode == 2, result.stdout + result.stderr
    assert "Traceback" not in result.stderr
    assert result.stderr.startswith("error:")


# --- 1. symlinked config files -------------------------------------------------


def test_symlinked_settings_and_claude_md_stay_links_with_mode(home: Path, tmp_path: Path) -> None:
    dotfiles = tmp_path / "dotfiles"
    dotfiles.mkdir()
    (dotfiles / "settings.json").write_text('{"env": {"A": "1"}}\n', encoding="utf-8")
    (dotfiles / "CLAUDE.md").write_text("# mine\n", encoding="utf-8")
    (dotfiles / "settings.json").chmod(0o600)
    (dotfiles / "CLAUDE.md").chmod(0o640)
    (home / ".claude").mkdir()
    (home / ".claude/settings.json").symlink_to(dotfiles / "settings.json")
    (home / ".claude/CLAUDE.md").symlink_to(dotfiles / "CLAUDE.md")

    ok(run_aicj("install", home=home))
    assert (home / ".claude/settings.json").is_symlink()
    assert (home / ".claude/CLAUDE.md").is_symlink()
    assert "/hooks/aicj/" in (dotfiles / "settings.json").read_text(encoding="utf-8")
    assert BEGIN in (dotfiles / "CLAUDE.md").read_text(encoding="utf-8")
    assert stat.S_IMODE((dotfiles / "settings.json").stat().st_mode) == 0o600
    assert stat.S_IMODE((dotfiles / "CLAUDE.md").stat().st_mode) == 0o640

    ok(run_aicj("uninstall", home=home))
    assert (home / ".claude/settings.json").is_symlink()
    assert (home / ".claude/CLAUDE.md").is_symlink()
    assert json.loads((dotfiles / "settings.json").read_text(encoding="utf-8")) == {"env": {"A": "1"}}
    assert (dotfiles / "CLAUDE.md").read_text(encoding="utf-8") == "# mine\n"


def test_atomic_write_new_file_is_0644_and_keeps_existing_mode(tmp_path: Path) -> None:
    fresh = tmp_path / "new.txt"
    util.atomic_write(fresh, b"x")
    assert stat.S_IMODE(fresh.stat().st_mode) == 0o644
    existing = tmp_path / "old.txt"
    existing.write_bytes(b"a")
    existing.chmod(0o600)
    util.atomic_write(existing, b"b")
    assert stat.S_IMODE(existing.stat().st_mode) == 0o600


def test_unique_backup_rel_never_reuses_a_name(tmp_path: Path) -> None:
    (tmp_path / "f.txt.aicj-bak-1").write_text("a", encoding="utf-8")
    second = util.unique_backup_rel(tmp_path, "f.txt", "1")
    assert second != "f.txt.aicj-bak-1"
    (tmp_path / second).write_text("b", encoding="utf-8")
    assert util.unique_backup_rel(tmp_path, "f.txt", "1") not in ("f.txt.aicj-bak-1", second)


# --- 2. failure consistency ----------------------------------------------------


def test_blocked_parent_aborts_before_any_write_and_rerun_works(home: Path) -> None:
    (home / ".claude").mkdir()
    (home / ".claude/hooks").write_text("i am a file\n", encoding="utf-8")
    refused(run_aicj("install", home=home))
    assert files_under(home) == [".claude/hooks"]

    (home / ".claude/hooks").unlink()
    ok(run_aicj("install", home=home))
    ok(run_aicj("uninstall", home=home))
    assert files_under(home) == []


def test_non_utf8_claude_md_aborts_without_writing(home: Path) -> None:
    claude_md = home / ".claude/CLAUDE.md"
    claude_md.parent.mkdir()
    claude_md.write_bytes(b"\xff\xfe broken")
    refused(run_aicj("install", home=home))
    assert claude_md.read_bytes() == b"\xff\xfe broken"
    assert files_under(home) == [".claude/CLAUDE.md"]


@pytest.mark.skipif(os.geteuid() == 0, reason="permission failure cannot be simulated as root")
def test_midway_failure_leaves_log_and_rerun_then_uninstall_is_clean(home: Path) -> None:
    skills = home / ".claude/skills"
    skills.mkdir(parents=True)
    skills.chmod(0o555)
    try:
        failed = run_aicj("install", home=home)
        refused(failed)
        log = manifest_of(home)
        assert log["state"] == "in-progress"
        assert ".claude/rules/core-sample.md" in {e["path"] for e in log["entries"]}
        assert (home / ".claude/rules/core-sample.md").is_file()
    finally:
        skills.chmod(0o755)

    ok(run_aicj("install", home=home))
    assert manifest_of(home)["state"] == "complete"
    assert entry_of(home, ".claude/rules/core-sample.md")["action"] == "created"
    ok(run_aicj("uninstall", home=home))
    assert files_under(home) == []


@pytest.mark.skipif(os.geteuid() == 0, reason="permission failure cannot be simulated as root")
def test_uninstall_after_interrupted_install_leaves_nothing(home: Path) -> None:
    skills = home / ".claude/skills"
    skills.mkdir(parents=True)
    skills.chmod(0o555)
    try:
        refused(run_aicj("install", home=home))
    finally:
        skills.chmod(0o755)
    ok(run_aicj("uninstall", home=home))
    assert files_under(home) == []


# --- 3. link mode --------------------------------------------------------------


def test_link_install_then_source_edit_still_uninstalls_clean(home: Path, tmp_path: Path) -> None:
    source = fixture_copy(tmp_path)
    ok(run_aicj("install", "--link", home=home, source=source))
    entry = entry_of(home, ".claude/rules/core-sample.md")
    assert entry["kind"] == "symlink"
    assert entry["link"] == os.path.realpath(source / "core/rules/core-sample.md")

    with (source / "core/rules/core-sample.md").open("a", encoding="utf-8") as handle:
        handle.write("edited upstream\n")
    doctor = run_aicj("doctor", home=home, source=source)
    assert "modified after install" not in doctor.stdout

    result = run_aicj("uninstall", home=home, source=source)
    ok(result)
    assert "modified after install" not in result.stdout
    assert files_under(home) == []
    assert (source / "core/rules/core-sample.md").is_file()


def test_status_counts_link_install_as_installed(home: Path) -> None:
    ok(run_aicj("install", "--link", home=home))
    status = run_aicj("status", home=home)
    ok(status)
    line = next(l for l in status.stdout.splitlines() if ".claude/rules/core-sample.md" in l)
    assert line.startswith("installed")


def test_link_and_copy_modes_can_be_toggled(home: Path) -> None:
    rule = home / ".claude/rules/core-sample.md"
    ok(run_aicj("install", "--link", home=home))
    assert rule.is_symlink()
    ok(run_aicj("install", home=home))
    assert rule.is_file() and not rule.is_symlink()
    assert entry_of(home, ".claude/rules/core-sample.md")["kind"] == "file"
    assert entry_of(home, ".claude/rules/core-sample.md")["action"] == "created"
    ok(run_aicj("install", "--link", home=home))
    assert rule.is_symlink()
    assert entry_of(home, ".claude/rules/core-sample.md")["kind"] == "symlink"
    ok(run_aicj("uninstall", home=home))
    assert files_under(home) == []


def test_install_ignores_python_cache_artifacts(home: Path, tmp_path: Path) -> None:
    source = fixture_copy(tmp_path)
    cache = source / "core/skills/sample-skill/__pycache__"
    cache.mkdir()
    (cache / "x.pyc").write_bytes(b"compiled")
    (source / "core/skills/sample-skill/x.pyo").write_bytes(b"optimized")

    dry_run = run_aicj("install", "--dry-run", home=home, source=source)
    ok(dry_run)
    assert "__pycache__" not in dry_run.stdout
    assert ".pyo" not in dry_run.stdout

    ok(run_aicj("install", home=home, source=source))
    installed = files_under(home)
    assert ".claude/skills/sample-skill/__pycache__/x.pyc" not in installed
    assert ".claude/skills/sample-skill/x.pyo" not in installed


# --- 4. marker block -----------------------------------------------------------

MALFORMED = {
    "only-begin": f"top\n{BEGIN}\nPRECIOUS\n",
    "only-end": f"top\n{END}\nPRECIOUS\n",
    "duplicate": f"{BEGIN}\na\n{END}\n{BEGIN}\nb\n{END}\n",
    "reversed": f"{END}\nmiddle\n{BEGIN}\n",
}


@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_malformed_block_refused_by_install_and_file_unchanged(home: Path, name: str) -> None:
    claude_md = home / ".claude/CLAUDE.md"
    claude_md.parent.mkdir()
    claude_md.write_text(MALFORMED[name], encoding="utf-8")
    refused(run_aicj("install", home=home))
    assert claude_md.read_text(encoding="utf-8") == MALFORMED[name]
    assert files_under(home) == [".claude/CLAUDE.md"]


@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_malformed_block_refused_by_uninstall_and_nothing_removed(home: Path, name: str) -> None:
    ok(run_aicj("install", home=home))
    claude_md = home / ".claude/CLAUDE.md"
    claude_md.write_text(MALFORMED[name], encoding="utf-8")
    before = snapshot(home)
    refused(run_aicj("uninstall", home=home))
    assert snapshot(home) == before


def test_uninstall_keeps_an_edited_block(home: Path) -> None:
    ok(run_aicj("install", home=home))
    claude_md = home / ".claude/CLAUDE.md"
    claude_md.write_text(claude_md.read_text(encoding="utf-8").replace("@aicj", "@mine"), encoding="utf-8")
    result = run_aicj("uninstall", home=home)
    ok(result)
    assert "edited after install" in result.stdout
    assert "@mine" in claude_md.read_text(encoding="utf-8")


def test_preexisting_block_is_adopted_and_survives_uninstall(home: Path) -> None:
    claude_md = home / ".claude/CLAUDE.md"
    claude_md.parent.mkdir()
    text = f"u\n{BEGIN}\n@aicj/CLAUDE.global.md\n{END}\n"
    claude_md.write_text(text, encoding="utf-8")
    ok(run_aicj("install", home=home))
    assert entry_of(home, ".claude/CLAUDE.md")["action"] == "adopted"
    ok(run_aicj("uninstall", home=home))
    assert claude_md.read_text(encoding="utf-8") == text


# --- 5. skills install as a unit -----------------------------------------------


def skill_source(tmp_path: Path) -> Path:
    source = fixture_copy(tmp_path)
    (source / "core/skills/sample-skill/helper.py").write_text("print('helper')\n", encoding="utf-8")
    return source


def test_partial_skill_conflict_skips_whole_skill_and_codex_link(home: Path, tmp_path: Path) -> None:
    source = skill_source(tmp_path)
    skill = home / ".claude/skills/sample-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("my own skill\n", encoding="utf-8")

    result = run_aicj("install", "--codex", home=home, source=source)
    ok(result)
    assert sorted(p.name for p in skill.iterdir()) == ["SKILL.md"]
    assert (skill / "SKILL.md").read_text(encoding="utf-8") == "my own skill\n"
    assert not (home / ".agents/skills/sample-skill").exists()
    assert not (home / ".agents/skills/sample-skill").is_symlink()
    assert entry_of(home, ".claude/skills/sample-skill/helper.py")["action"] == "skipped"
    assert entry_of(home, ".claude/skills/sample-skill/SKILL.md")["action"] == "skipped"

    ok(run_aicj("uninstall", home=home))
    assert (skill / "SKILL.md").read_text(encoding="utf-8") == "my own skill\n"


def test_skill_conflict_with_backup_moves_whole_directory_and_uninstall_restores(home: Path, tmp_path: Path) -> None:
    source = skill_source(tmp_path)
    skill = home / ".claude/skills/sample-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("my own skill\n", encoding="utf-8")
    (skill / "notes.txt").write_text("mine too\n", encoding="utf-8")

    ok(run_aicj("install", "--on-conflict", "backup", "--codex", home=home, source=source))
    assert sorted(p.name for p in skill.iterdir()) == ["SKILL.md", "helper.py"]
    backups = list((home / ".claude/skills").glob("sample-skill.aicj-bak-*"))
    assert len(backups) == 1
    assert (backups[0] / "notes.txt").read_text(encoding="utf-8") == "mine too\n"
    assert (home / ".agents/skills/sample-skill").is_symlink()

    ok(run_aicj("uninstall", home=home))
    assert sorted(p.name for p in skill.iterdir()) == ["SKILL.md", "notes.txt"]
    assert (skill / "SKILL.md").read_text(encoding="utf-8") == "my own skill\n"
    assert not list((home / ".claude/skills").glob("*.aicj-bak-*"))
    assert not (home / ".agents/skills/sample-skill").is_symlink()


# --- 7/8/15. hooks -------------------------------------------------------------


def test_hook_script_path_traversal_is_refused(home: Path, tmp_path: Path) -> None:
    source = fixture_copy(tmp_path)
    edit_json(
        source / "core/manifest.json",
        lambda d: d["hooks"].append({"event": "Stop", "script": "hooks/aicj/../../../evil.sh"}),
    )
    refused(run_aicj("install", home=home, source=source))
    assert files_under(home) == []


def test_hook_command_works_when_home_contains_spaces(tmp_path: Path) -> None:
    spaced = tmp_path / "my home"
    spaced.mkdir()
    ok(run_aicj("install", home=spaced))
    settings = json.loads((spaced / ".claude/settings.json").read_text(encoding="utf-8"))
    command = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert "'" in command
    run = subprocess.run(command, shell=True, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    strict = run_aicj("install", "--strict", home=spaced)
    ok(strict)
    settings = json.loads((spaced / ".claude/settings.json").read_text(encoding="utf-8"))
    command = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert subprocess.run(command, shell=True, capture_output=True, text=True).returncode == 2


def test_hook_with_skipped_script_is_not_registered(home: Path) -> None:
    script = home / ".claude/hooks/aicj/sample-hook.py"
    script.parent.mkdir(parents=True)
    script.write_text("# the user's own script\n", encoding="utf-8")
    result = run_aicj("install", home=home)
    ok(result)
    assert "hooks" not in json.loads((home / ".claude/settings.json").read_text(encoding="utf-8")) if (
        home / ".claude/settings.json"
    ).exists() else True
    assert "script not installed" in result.stdout
    assert manifest_of(home)["settings_hooks"] == []


def test_user_preexisting_identical_hook_is_adopted_and_survives_uninstall(home: Path) -> None:
    command = f"python3 {shlex.quote(str(home / '.claude/hooks/aicj/sample-hook.py'))}"
    settings_path = home / ".claude/settings.json"
    settings_path.parent.mkdir()
    original = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": command}]}]}}
    settings_path.write_text(json.dumps(original), encoding="utf-8")

    ok(run_aicj("install", home=home))
    assert manifest_of(home)["settings_hooks"] == []
    ok(run_aicj("install", home=home))
    assert manifest_of(home)["settings_hooks"] == []
    ok(run_aicj("uninstall", home=home))
    assert json.loads(settings_path.read_text(encoding="utf-8")) == original


def test_reinstall_keeps_ownership_of_hooks_we_added(home: Path) -> None:
    ok(run_aicj("install", home=home))
    ok(run_aicj("install", home=home))
    assert len(manifest_of(home)["settings_hooks"]) == 1
    ok(run_aicj("uninstall", home=home))
    assert files_under(home) == []


def test_events_without_matcher_get_no_matcher_key(home: Path, tmp_path: Path) -> None:
    source = fixture_copy(tmp_path)

    def add(data: dict) -> None:
        data["hooks"].append({"event": "Stop", "matcher": "ignored", "script": "hooks/aicj/sample-hook.py"})
        data["hooks"].append({"event": "SessionStart", "script": "hooks/aicj/sample-hook.py"})

    edit_json(source / "core/manifest.json", add)
    ok(run_aicj("install", home=home, source=source))
    settings_path = home / ".claude/settings.json"
    hooks = json.loads(settings_path.read_text(encoding="utf-8"))["hooks"]
    assert "matcher" not in hooks["Stop"][0]
    assert "matcher" not in hooks["SessionStart"][0]
    assert hooks["PreToolUse"][0]["matcher"] == "Bash"

    frozen = settings_path.read_bytes()
    ok(run_aicj("install", home=home, source=source))
    assert settings_path.read_bytes() == frozen
    ok(run_aicj("uninstall", home=home, source=source))
    assert files_under(home) == []


# --- 11. component index -------------------------------------------------------


@pytest.mark.parametrize("target", ["settings.json", "CLAUDE.md", "aicj/manifest.json", "SETTINGS.JSON"])
def test_index_rejects_reserved_targets(home: Path, tmp_path: Path, target: str) -> None:
    source = fixture_copy(tmp_path)
    edit_json(
        source / "core/manifest.json",
        lambda d: d["entries"]["rules"].append({"source": "rules/core-sample.md", "target": target}),
    )
    refused(run_aicj("install", home=home, source=source))
    assert files_under(home) == []


def test_index_rejects_duplicate_targets(home: Path, tmp_path: Path) -> None:
    source = fixture_copy(tmp_path)
    edit_json(
        source / "packs/java/pack.json",
        lambda d: d["entries"]["rules"].append({"source": "rules/pack-sample.md", "target": "rules/core-sample.md"}),
    )
    refused(run_aicj("install", home=home, source=source))
    assert files_under(home) == []


def test_index_rejects_source_outside_component_root(home: Path, tmp_path: Path) -> None:
    source = fixture_copy(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("secret\n", encoding="utf-8")
    edit_json(
        source / "core/manifest.json",
        lambda d: d["entries"]["refs"].append({"source": str(outside), "target": "refs/outside.md"}),
    )
    refused(run_aicj("install", home=home, source=source))
    assert files_under(home) == []


def test_index_skips_symlinks_inside_directory_sources(home: Path, tmp_path: Path) -> None:
    source = fixture_copy(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("secret\n", encoding="utf-8")
    (source / "core/skills/sample-skill/leak.md").symlink_to(outside)
    ok(run_aicj("install", home=home, source=source))
    assert not (home / ".claude/skills/sample-skill/leak.md").exists()
    assert (home / ".claude/skills/sample-skill/SKILL.md").is_file()


# --- 12. manifest loading ------------------------------------------------------


@pytest.mark.parametrize("bad", ["/etc/hosts", "../escape.txt", ".claude/../../escape.txt", "etc/passwd", ".claude"])
def test_manifest_with_hostile_entry_path_is_rejected(home: Path, tmp_path: Path, bad: str) -> None:
    ok(run_aicj("install", home=home))
    victim = tmp_path / "escape.txt"
    victim.write_text("victim\n", encoding="utf-8")
    path = home / ".claude/aicj/manifest.json"
    edit_json(path, lambda d: d["entries"].append({"path": bad, "kind": "file", "action": "created", "sha256": ""}))
    before = snapshot(home)
    refused(run_aicj("uninstall", home=home))
    assert snapshot(home) == before
    assert victim.read_text(encoding="utf-8") == "victim\n"


def test_manifest_with_hostile_backup_or_dir_is_rejected(home: Path) -> None:
    ok(run_aicj("install", home=home))
    path = home / ".claude/aicj/manifest.json"
    edit_json(path, lambda d: d["entries"][0].update(backup="../../x"))
    refused(run_aicj("uninstall", home=home))
    ok_path = json.loads(path.read_text(encoding="utf-8"))
    ok_path["entries"][0]["backup"] = ""
    ok_path["created_dirs"].append("/tmp")
    path.write_text(json.dumps(ok_path), encoding="utf-8")
    refused(run_aicj("uninstall", home=home))


@pytest.mark.parametrize("version", [2, 0, "1", None])
def test_manifest_with_unknown_version_is_rejected(home: Path, version) -> None:
    ok(run_aicj("install", home=home))
    path = home / ".claude/aicj/manifest.json"
    edit_json(path, lambda d: d.update(version=version))
    refused(run_aicj("uninstall", home=home))
    assert (home / ".claude/rules/core-sample.md").is_file()


def test_entry_without_checksum_is_kept_with_a_warning(home: Path) -> None:
    ok(run_aicj("install", home=home))
    path = home / ".claude/aicj/manifest.json"
    edit_json(
        path,
        lambda d: [e.update(sha256="") for e in d["entries"] if e["path"] == ".claude/rules/core-sample.md"],
    )
    result = run_aicj("uninstall", home=home)
    ok(result)
    assert "no checksum recorded" in result.stdout
    assert (home / ".claude/rules/core-sample.md").is_file()


# --- 13. replaced files --------------------------------------------------------


def test_modified_replaced_file_is_kept_and_manifest_still_tracks_backup(home: Path) -> None:
    target = home / ".claude/rules/core-sample.md"
    target.parent.mkdir(parents=True)
    target.write_text("original\n", encoding="utf-8")
    ok(run_aicj("install", "--on-conflict", "backup", home=home))
    backup = entry_of(home, ".claude/rules/core-sample.md")["backup"]
    assert (home / backup).read_text(encoding="utf-8") == "original\n"

    target.write_text("edited later\n", encoding="utf-8")
    result = run_aicj("uninstall", home=home)
    ok(result)
    assert target.read_text(encoding="utf-8") == "edited later\n"
    assert backup in result.stdout
    assert (home / backup).is_file()
    left = manifest_of(home)
    assert [e["path"] for e in left["entries"]] == [".claude/rules/core-sample.md"]
    assert left["entries"][0]["backup"] == backup
    assert not (home / ".claude/hooks/aicj/sample-hook.py").exists()


def test_second_backup_keeps_the_earliest_user_original(home: Path) -> None:
    target = home / ".claude/rules/core-sample.md"
    target.parent.mkdir(parents=True)
    target.write_text("original\n", encoding="utf-8")
    ok(run_aicj("install", "--on-conflict", "backup", home=home))
    first = entry_of(home, ".claude/rules/core-sample.md")["backup"]

    target.write_text("edit two\n", encoding="utf-8")
    ok(run_aicj("install", "--on-conflict", "backup", home=home))
    entry = entry_of(home, ".claude/rules/core-sample.md")
    assert entry["action"] == "replaced"
    assert entry["backup"] == first
    assert (home / first).read_text(encoding="utf-8") == "original\n"
    copies = sorted(p.read_text(encoding="utf-8") for p in (home / ".claude/rules").glob("core-sample.md.aicj-bak-*"))
    assert copies == ["edit two\n", "original\n"]

    ok(run_aicj("uninstall", home=home))
    assert target.read_text(encoding="utf-8") == "original\n"


# --- 14. settings backups ------------------------------------------------------


def test_settings_backup_is_single_and_cleaned_after_full_restore(home: Path) -> None:
    settings_path = home / ".claude/settings.json"
    settings_path.parent.mkdir()
    original = {"env": {"A": "1"}}
    settings_path.write_text(json.dumps(original), encoding="utf-8")

    ok(run_aicj("install", home=home))
    assert len(list((home / ".claude").glob("settings.json.aicj-bak-*"))) == 1
    ok(run_aicj("install", "--strict", home=home))
    assert len(list((home / ".claude").glob("settings.json.aicj-bak-*"))) == 1
    ok(run_aicj("uninstall", home=home))
    assert json.loads(settings_path.read_text(encoding="utf-8")) == original
    assert files_under(home) == [".claude/settings.json"]


def test_backup_of_settings_we_created_is_removed_with_it(home: Path) -> None:
    ok(run_aicj("install", home=home))
    ok(run_aicj("install", "--strict", home=home))
    ok(run_aicj("uninstall", home=home))
    assert files_under(home) == []


def test_first_backup_taken_on_clean_restore_is_removed(home: Path) -> None:
    settings_path = home / ".claude/settings.json"
    settings_path.parent.mkdir()
    settings_path.write_text("{}\n", encoding="utf-8")
    ok(run_aicj("install", home=home))
    ok(run_aicj("uninstall", home=home))
    assert not list((home / ".claude").glob("*.aicj-bak-*"))


# --- 16. doctor, dry-run, directories ------------------------------------------


def test_doctor_warns_instead_of_crashing_on_non_utf8_claude_md(home: Path) -> None:
    ok(run_aicj("install", home=home))
    (home / ".claude/CLAUDE.md").write_bytes(b"\xff\xfe broken")
    doctor = run_aicj("doctor", home=home)
    assert doctor.returncode == 0, doctor.stdout + doctor.stderr
    assert "Traceback" not in doctor.stderr
    assert any(line.startswith("WARN") and "UTF-8" in line for line in doctor.stdout.splitlines())


def test_doctor_warns_on_malformed_marker_block(home: Path) -> None:
    ok(run_aicj("install", home=home))
    (home / ".claude/CLAUDE.md").write_text(f"{BEGIN}\n", encoding="utf-8")
    doctor = run_aicj("doctor", home=home)
    assert doctor.returncode == 0, doctor.stdout + doctor.stderr
    assert any(line.startswith("WARN") and "malformed" in line for line in doctor.stdout.splitlines())


def test_uninstall_dry_run_reports_keep_for_modified_files(home: Path) -> None:
    ok(run_aicj("install", home=home))
    (home / ".claude/rules/core-sample.md").write_text("user edit\n", encoding="utf-8")
    before = snapshot(home)
    result = run_aicj("uninstall", "--dry-run", home=home)
    ok(result)
    assert snapshot(home) == before
    assert "modified after install" in result.stdout
    removed = [l for l in result.stdout.splitlines() if l.startswith("removed") and "core-sample.md" in l]
    assert removed == []
    assert any(l.startswith("removed") and "pack-sample.md" in l for l in result.stdout.splitlines())


def test_uninstall_only_prunes_directories_it_created(home: Path) -> None:
    (home / ".claude/rules").mkdir(parents=True)
    (home / ".claude/skills").mkdir()
    ok(run_aicj("install", home=home))
    created = set(manifest_of(home)["created_dirs"])
    assert ".claude/rules" not in created
    assert ".claude/skills" not in created
    assert ".claude/aicj" in created
    ok(run_aicj("uninstall", home=home))
    assert (home / ".claude/rules").is_dir()
    assert (home / ".claude/skills").is_dir()
    assert not (home / ".claude/aicj").exists()
    assert not (home / ".claude/hooks").exists()
    assert not list((home / ".claude/skills").iterdir())


def test_kept_manifest_keeps_created_dirs_so_a_later_uninstall_can_prune(home: Path) -> None:
    target = home / ".claude/rules/core-sample.md"
    target.parent.mkdir(parents=True)
    target.write_text("original\n", encoding="utf-8")
    ok(run_aicj("install", "--on-conflict", "backup", home=home))
    target.write_text("edited\n", encoding="utf-8")
    ok(run_aicj("uninstall", home=home))
    assert (home / ".claude/aicj/manifest.json").is_file()
    target.unlink()
    ok(run_aicj("uninstall", home=home))
    assert not (home / ".claude/aicj").exists()


def test_cli_entry_point_is_runnable() -> None:
    result = subprocess.run([sys.executable, str(AICJ), "--help"], capture_output=True, text=True)
    assert result.returncode == 0


# --- 17. optional hooks ---------------------------------------------------------


def _fixture_with_optional_hook(tmp_path: Path) -> Path:
    source = fixture_copy(tmp_path)
    (source / "core/hooks/aicj/optional-hook.py").write_text(
        "import os, sys\nsys.exit(2 if os.environ.get(\"AICJ_HOOK_MODE\") == \"block\" else 0)\n",
        encoding="utf-8",
    )
    edit_json(source / "core/manifest.json", _add_optional_hook)
    return source


def _add_optional_hook(data: dict) -> None:
    data["entries"]["hooks"].append(
        {"source": "hooks/aicj/optional-hook.py", "target": "hooks/aicj/optional-hook.py"}
    )
    data["hooks"].append(
        {"event": "PreToolUse", "matcher": "Bash", "script": "hooks/aicj/optional-hook.py", "optional": True}
    )


def test_optional_hook_not_registered_by_default(home: Path, tmp_path: Path) -> None:
    source = _fixture_with_optional_hook(tmp_path)
    result = run_aicj("install", home=home, source=source)
    ok(result)
    hooks = json.loads((home / ".claude/settings.json").read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    assert len(hooks) == 1  # only the non-optional sample hook
    assert "可选钩子未启用" in result.stdout
    # the script file itself still installed
    assert (home / ".claude/hooks/aicj/sample-hook.py").is_file()


def test_optional_hook_registered_when_named(home: Path, tmp_path: Path) -> None:
    source = _fixture_with_optional_hook(tmp_path)
    result = run_aicj("install", "--enable-hook", "optional-hook", home=home, source=source)
    ok(result)
    hooks = json.loads((home / ".claude/settings.json").read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    assert len(hooks) == 2
    assert "可选钩子未启用" not in result.stdout

    doctor = run_aicj("doctor", home=home, source=source)
    ok(doctor)
    assert "MISSING" not in doctor.stdout


def test_optional_hook_removed_when_reinstall_omits_the_name(home: Path, tmp_path: Path) -> None:
    source = _fixture_with_optional_hook(tmp_path)
    ok(run_aicj("install", "--enable-hook", "optional-hook", home=home, source=source))
    result = run_aicj("install", home=home, source=source)
    ok(result)
    hooks = json.loads((home / ".claude/settings.json").read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    assert len(hooks) == 1
    assert "可选钩子未启用：optional-hook" in result.stdout

    ok(run_aicj("uninstall", home=home, source=source))
    assert files_under(home) == []


def test_unknown_enable_hook_name_is_refused(home: Path, tmp_path: Path) -> None:
    source = _fixture_with_optional_hook(tmp_path)
    result = run_aicj("install", "--enable-hook", "no-such-hook", home=home, source=source)
    refused(result)
    assert "no-such-hook" in result.stderr
    assert files_under(home) == []


def test_doctor_skips_disabled_optional_hooks(home: Path, tmp_path: Path) -> None:
    source = _fixture_with_optional_hook(tmp_path)
    ok(run_aicj("install", home=home, source=source))
    doctor = run_aicj("doctor", home=home, source=source)
    ok(doctor)
    line = next(l for l in doctor.stdout.splitlines() if "optional hook optional-hook" in l)
    assert line.startswith("SKIPPED")
    assert "MISSING" not in doctor.stdout
