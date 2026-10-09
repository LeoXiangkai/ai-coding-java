from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from installer.lib import index

REPO = Path(__file__).resolve().parents[1]
PACK = REPO / "packs/vue"
DETECT = PACK / "skills/vue-verify/scripts/detect_vue.py"
STATIC = PACK / "skills/vue-verify/scripts/static_review.py"
FIXTURES = REPO / "tests/packs/vue/fixtures"
AICJ = REPO / "installer/aicj.py"


def run_detect(name: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(DETECT), str(FIXTURES / name)],
        capture_output=True,
        text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_manifest_entries_and_rule_frontmatter():
    data = json.loads((PACK / "pack.json").read_text(encoding="utf-8"))
    assert data["detect"] == {"files": [], "package_deps": ["vue"]}
    assert [row["target"] for row in data["entries"]["rules"]] == [
        "rules/vue3-typescript.md",
        "rules/vue2-legacy.md",
    ]
    assert [row["target"] for row in data["entries"]["skills"]] == [
        "skills/vue-verify",
        "skills/playwright-ui-auto",
    ]
    for path in sorted((PACK / "rules").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\npaths:\n")
        assert len(text.encode("utf-8")) <= 4096


def test_detect_vue3_vite_typescript_fixture_fields():
    result = run_detect("vue3-vite-ts-pnpm")
    assert result["vue_major"] == 3
    assert result["build_tool"] == "vite"
    assert result["typescript"] is True
    assert result["ui_lib"] == ["element-plus"]
    assert result["state"] == ["pinia"]
    assert result["test_runner"] == "vitest"
    assert result["package_manager"] == "pnpm"
    assert result["scripts"] == {
        "lint": "pnpm run lint",
        "type_check": "pnpm run type-check",
        "test": "pnpm run test:unit",
        "build": "pnpm run build",
        "dev": "pnpm run dev",
    }
    assert result["playwright"] is True


def test_detect_vue2_cli_yarn_fixture_fields():
    result = run_detect("vue2-cli-yarn")
    assert result["vue_major"] == 2
    assert result["build_tool"] == "vue-cli"
    assert result["typescript"] is False
    assert result["ui_lib"] == ["element-ui"]
    assert result["state"] == ["vuex"]
    assert result["test_runner"] == "jest"
    assert result["package_manager"] == "yarn"
    assert result["scripts"] == {
        "lint": "yarn run lint",
        "type_check": "MISSING",
        "test": "yarn run test",
        "build": "yarn run build",
        "dev": "yarn run serve",
    }
    assert result["playwright"] is False


def test_detect_missing_and_invalid_package_json_return_defaults():
    expected = {
        "vue_major": None,
        "build_tool": "unknown",
        "typescript": False,
        "ui_lib": [],
        "state": [],
        "test_runner": None,
        "package_manager": "npm",
        "scripts": {
            "lint": "MISSING",
            "type_check": "MISSING",
            "test": "MISSING",
            "build": "MISSING",
            "dev": "MISSING",
        },
        "playwright": False,
    }
    assert run_detect("no-package") == expected
    assert run_detect("bad-json") == expected


def test_resolve_packs_detects_vue_dependency_only(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"dependencies":{"vue":"3.4.0"}}', encoding="utf-8")
    assert index.resolve_packs("auto", tmp_path, ["vue"], False) == ["vue"]
    (tmp_path / "package.json").write_text('{"dependencies":{"react":"18.0.0"}}', encoding="utf-8")
    assert index.resolve_packs("auto", tmp_path, ["vue"], False) == []


def test_install_doctor_uninstall_vue_pack(tmp_path: Path):
    home = tmp_path / "home"
    home.mkdir()
    install = subprocess.run(
        [sys.executable, str(AICJ), "install", "--home", str(home), "--source", str(REPO), "--packs", "vue"],
        capture_output=True,
        text=True, encoding="utf-8",
    )
    assert install.returncode == 0, install.stdout + install.stderr
    for name in ("vue3-typescript.md", "vue2-legacy.md"):
        assert (home / ".claude/rules" / name).is_file()
    for skill in ("vue-verify", "playwright-ui-auto"):
        assert (home / ".claude/skills" / skill / "SKILL.md").is_file()
    assert (home / ".claude/skills/vue-verify/scripts/static_review.py").is_file()
    doctor = subprocess.run(
        [sys.executable, str(AICJ), "doctor", "--home", str(home)],
        capture_output=True,
        text=True, encoding="utf-8",
    )
    assert doctor.returncode == 0, doctor.stdout + doctor.stderr
    assert "MISSING" not in doctor.stdout
    uninstall = subprocess.run(
        [sys.executable, str(AICJ), "uninstall", "--home", str(home)],
        capture_output=True,
        text=True, encoding="utf-8",
    )
    assert uninstall.returncode == 0, uninstall.stdout + uninstall.stderr
    assert list(home.rglob("*")) == []


def test_rules_have_paths_and_pack_is_sanitized():
    for path in PACK.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            assert "/Users/" not in text
            assert "/home/" not in text
            assert "gpt-" not in text.lower()
            assert "claude-" not in text.lower()
    for path in (PACK / "rules").glob("*.md"):
        assert "paths:" in path.read_text(encoding="utf-8")


def test_vue_static_review_good_fixture_has_no_findings():
    result = subprocess.run(
        [sys.executable, str(STATIC), str(FIXTURES / "static/good")],
        capture_output=True,
        text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Scanned files: 1" in result.stdout
    assert "No P0/P1 deterministic findings." in result.stdout


def test_vue_static_review_bad_fixture_hits_every_rule():
    result = subprocess.run(
        [sys.executable, str(STATIC), str(FIXTURES / "static/bad/x.vue")],
        capture_output=True,
        text=True, encoding="utf-8",
    )
    assert result.returncode == 2, result.stdout + result.stderr
    for message in (
        "possible plaintext secret",
        "v-html may create an XSS risk",
        "dynamic code execution",
        "v-for should define a key",
        "debug output or debugger statement",
        "explicit TypeScript any",
        "v-if and v-for should not share a tag",
    ):
        assert message in result.stdout


def test_vue_static_review_skips_marked_fixture_directory_but_scans_explicit_file():
    directory = subprocess.run(
        [sys.executable, str(STATIC), str(FIXTURES / "static/bad")],
        capture_output=True,
        text=True, encoding="utf-8",
    )
    assert directory.returncode == 0
    assert directory.stdout.splitlines()[0] == "Scanned files: 0"


def test_detect_vue_includes_static_command_path():
    result = run_detect("vue3-vite-ts-pnpm")
    command = result["static"]
    expected = (f'"{Path(sys.executable).resolve()}" "{STATIC.resolve()}" <paths>'
                if sys.platform == "win32" else f"python3 {STATIC} <paths>")
    assert command == expected
    assert STATIC.resolve().is_file()
