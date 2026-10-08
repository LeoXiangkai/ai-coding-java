from __future__ import annotations

import json
from pathlib import Path

from conftest import FIXTURE, files_under, run_aicj, snapshot


def manifest_of(home: Path) -> dict:
    return json.loads((home / ".claude/aicj/manifest.json").read_text(encoding="utf-8"))


def actions_of(home: Path) -> dict[str, str]:
    return {entry["path"]: entry["action"] for entry in manifest_of(home)["entries"]}


def test_install_uninstall_round_trip_leaves_no_residue(home: Path) -> None:
    result = run_aicj("install", home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (home / ".claude/rules/core-sample.md").is_file()
    assert (home / ".claude/skills/sample-skill/SKILL.md").is_file()
    assert (home / ".claude/hooks/aicj/sample-hook.py").is_file()
    assert (home / ".claude/rules/pack-sample.md").is_file()
    assert (home / ".claude/settings.json").is_file()
    assert (home / ".claude/aicj/manifest.json").is_file()

    result = run_aicj("uninstall", home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert files_under(home) == []


def test_existing_same_content_is_adopted(home: Path) -> None:
    target = home / ".claude/rules/core-sample.md"
    target.parent.mkdir(parents=True)
    target.write_bytes((FIXTURE / "core/rules/core-sample.md").read_bytes())
    result = run_aicj("install", home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert actions_of(home)[".claude/rules/core-sample.md"] == "adopted"

    assert run_aicj("uninstall", home=home).returncode == 0
    assert target.is_file()


def test_reinstall_is_idempotent_and_uninstall_still_cleans(home: Path) -> None:
    assert run_aicj("install", home=home).returncode == 0
    before = snapshot(home, ignore=(".claude/aicj/manifest.json",))
    result = run_aicj("install", home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert snapshot(home, ignore=(".claude/aicj/manifest.json",)) == before
    assert actions_of(home)[".claude/rules/core-sample.md"] == "created"

    assert run_aicj("uninstall", home=home).returncode == 0
    assert files_under(home) == []


def test_conflict_default_skips_and_keeps_user_content(home: Path) -> None:
    target = home / ".claude/rules/core-sample.md"
    target.parent.mkdir(parents=True)
    target.write_text("user edit\n", encoding="utf-8")
    result = run_aicj("install", home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert target.read_text(encoding="utf-8") == "user edit\n"
    assert actions_of(home)[".claude/rules/core-sample.md"] == "skipped"
    assert "skipped" in result.stdout

    assert run_aicj("uninstall", home=home).returncode == 0
    assert target.read_text(encoding="utf-8") == "user edit\n"


def test_on_conflict_backup_replaces_and_uninstall_restores(home: Path) -> None:
    assert run_aicj("install", home=home).returncode == 0
    target = home / ".claude/rules/core-sample.md"
    target.write_text("user edit\n", encoding="utf-8")
    result = run_aicj("install", "--on-conflict", "backup", home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert actions_of(home)[".claude/rules/core-sample.md"] == "replaced"
    assert target.read_text(encoding="utf-8") == (FIXTURE / "core/rules/core-sample.md").read_text(encoding="utf-8")
    backups = list((home / ".claude/rules").glob("core-sample.md.aicj-bak-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "user edit\n"

    result = run_aicj("uninstall", home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert target.read_text(encoding="utf-8") == "user edit\n"


def test_uninstall_keeps_files_the_user_edited(home: Path) -> None:
    assert run_aicj("install", home=home).returncode == 0
    target = home / ".claude/rules/core-sample.md"
    target.write_text("user edit\n", encoding="utf-8")
    result = run_aicj("uninstall", home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert target.is_file()
    assert target.read_text(encoding="utf-8") == "user edit\n"
    assert "modified after install" in result.stdout


def test_symlink_to_source_is_adopted_symlink(home: Path) -> None:
    source = FIXTURE / "core/rules/core-sample.md"
    target = home / ".claude/rules/core-sample.md"
    target.parent.mkdir(parents=True)
    target.symlink_to(source)
    result = run_aicj("install", home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert actions_of(home)[".claude/rules/core-sample.md"] == "adopted-symlink"


def test_link_install_writes_symlinks_and_is_idempotent(home: Path) -> None:
    result = run_aicj("install", "--link", home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    target = home / ".claude/rules/core-sample.md"
    assert target.is_symlink()
    assert target.resolve() == (FIXTURE / "core/rules/core-sample.md").resolve()
    assert manifest_of(home)["options"]["link"] is True

    result = run_aicj("install", "--link", home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert actions_of(home)[".claude/rules/core-sample.md"] == "created"
    assert "adopted-symlink  .claude/rules/core-sample.md" in result.stdout

    assert run_aicj("uninstall", home=home).returncode == 0
    assert files_under(home) == []
    assert (FIXTURE / "core/rules/core-sample.md").is_file()


def test_settings_merge_keeps_user_entries_and_is_idempotent(home: Path) -> None:
    settings_path = home / ".claude/settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "env": {"A": "1"},
                "permissions": {"allow": ["Bash(ls)"]},
                "hooks": {
                    "PreToolUse": [
                        {"matcher": "Edit", "hooks": [{"type": "command", "command": "echo user"}]}
                    ]
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_aicj("install", home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    merged = json.loads(settings_path.read_text(encoding="utf-8"))
    assert merged["env"] == {"A": "1"}
    assert merged["permissions"] == {"allow": ["Bash(ls)"]}
    groups = merged["hooks"]["PreToolUse"]
    assert groups[0] == {"matcher": "Edit", "hooks": [{"type": "command", "command": "echo user"}]}
    assert groups[1]["matcher"] == "Bash"
    assert "/hooks/aicj/" in groups[1]["hooks"][0]["command"]

    frozen = settings_path.read_bytes()
    result = run_aicj("install", home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert settings_path.read_bytes() == frozen

    result = run_aicj("uninstall", home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    restored = json.loads(settings_path.read_text(encoding="utf-8"))
    assert restored["env"] == {"A": "1"}
    assert restored["permissions"] == {"allow": ["Bash(ls)"]}
    assert restored["hooks"]["PreToolUse"] == [
        {"matcher": "Edit", "hooks": [{"type": "command", "command": "echo user"}]}
    ]


def test_settings_uninstall_clears_empty_groups(home: Path) -> None:
    settings_path = home / ".claude/settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({"env": {"A": "1"}}) + "\n", encoding="utf-8")

    assert run_aicj("install", home=home).returncode == 0
    assert "hooks" in json.loads(settings_path.read_text(encoding="utf-8"))
    assert run_aicj("uninstall", home=home).returncode == 0
    assert json.loads(settings_path.read_text(encoding="utf-8")) == {"env": {"A": "1"}}


def test_settings_invalid_json_is_error_and_untouched(home: Path) -> None:
    settings_path = home / ".claude/settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("{not json", encoding="utf-8")
    before = settings_path.read_bytes()

    result = run_aicj("install", home=home)
    assert result.returncode == 2
    assert settings_path.read_bytes() == before
    assert files_under(home) == [".claude/settings.json"]


def test_claude_md_block_is_idempotent_and_removed_on_uninstall(home: Path) -> None:
    claude_md = home / ".claude/CLAUDE.md"
    claude_md.parent.mkdir(parents=True)
    claude_md.write_text("# user entry\n", encoding="utf-8")

    assert run_aicj("install", home=home).returncode == 0
    first = claude_md.read_text(encoding="utf-8")
    assert first.startswith("# user entry\n")
    assert first.count("<!-- aicj:begin -->") == 1
    assert "@aicj/CLAUDE.global.md" in first

    assert run_aicj("install", home=home).returncode == 0
    assert claude_md.read_text(encoding="utf-8") == first

    assert run_aicj("uninstall", home=home).returncode == 0
    assert claude_md.read_text(encoding="utf-8") == "# user entry\n"


def test_dry_run_install_and_uninstall_write_nothing(home: Path) -> None:
    before = snapshot(home)
    result = run_aicj("install", "--dry-run", home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert snapshot(home) == before
    assert before == {}

    assert run_aicj("install", home=home).returncode == 0
    installed = snapshot(home)
    result = run_aicj("uninstall", "--dry-run", home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert snapshot(home) == installed


def test_status_and_doctor_after_install(home: Path) -> None:
    assert run_aicj("install", home=home).returncode == 0
    status = run_aicj("status", home=home)
    assert status.returncode == 0, status.stdout + status.stderr
    assert "installed" in status.stdout
    assert ".claude/rules/core-sample.md" in status.stdout

    doctor = run_aicj("doctor", home=home)
    assert doctor.returncode == 0, doctor.stdout + doctor.stderr
    assert "MISSING" not in doctor.stdout
    assert "PASS" in doctor.stdout


def test_doctor_reports_missing_install(home: Path) -> None:
    doctor = run_aicj("doctor", home=home)
    assert doctor.returncode == 1
    assert "MISSING" in doctor.stdout


def test_install_option_flags_all_parse(home: Path) -> None:
    result = run_aicj(
        "install",
        "--dry-run",
        "--global",
        "--packs",
        "java,python,vue",
        "--adapters",
        "executor,lesson,jev,verify-probe",
        "--codex",
        "--codex-hooks",
        "--strict",
        "--link",
        "--on-conflict",
        "skip",
        home=home,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert snapshot(home) == {}


def test_codex_links_skills_and_strict_prefixes_hook(home: Path) -> None:
    result = run_aicj("install", "--codex", "--codex-hooks", "--strict", "--packs", "java", home=home)
    assert result.returncode == 0, result.stdout + result.stderr

    link = home / ".agents/skills/sample-skill"
    assert link.is_symlink()
    assert link.resolve() == (home / ".claude/skills/sample-skill").resolve()

    merged = json.loads((home / ".claude/settings.json").read_text(encoding="utf-8"))
    command = merged["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert command.startswith("AICJ_HOOK_MODE=block ")

    codex = json.loads((home / ".codex/hooks.json").read_text(encoding="utf-8"))
    assert "/hooks/aicj/" in codex["hooks"]["PreToolUse"][0]["hooks"][0]["command"]

    assert run_aicj("uninstall", home=home).returncode == 0
    assert not (home / ".agents/skills/sample-skill").is_symlink()


def test_project_scope_is_accepted(home: Path, tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    result = run_aicj("install", "--project", str(project), home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "project layer" in result.stdout


def test_uninstall_without_install_is_noop(home: Path) -> None:
    result = run_aicj("uninstall", home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert files_under(home) == []
