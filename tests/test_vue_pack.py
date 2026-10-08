from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from installer.lib import index

REPO = Path(__file__).resolve().parents[1]
PACK = REPO / "packs/vue"
DETECT = PACK / "skills/vue-verify/scripts/detect_vue.py"
FIXTURES = REPO / "tests/packs/vue/fixtures"
AICJ = REPO / "installer/aicj.py"


def run_detect(name: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(DETECT), str(FIXTURES / name)],
        capture_output=True,
        text=True,
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
        text=True,
    )
    assert install.returncode == 0, install.stdout + install.stderr
    for name in ("vue3-typescript.md", "vue2-legacy.md"):
        assert (home / ".claude/rules" / name).is_file()
    for skill in ("vue-verify", "playwright-ui-auto"):
        assert (home / ".claude/skills" / skill / "SKILL.md").is_file()
    doctor = subprocess.run(
        [sys.executable, str(AICJ), "doctor", "--home", str(home)],
        capture_output=True,
        text=True,
    )
    assert doctor.returncode == 0, doctor.stdout + doctor.stderr
    assert "MISSING" not in doctor.stdout
    uninstall = subprocess.run(
        [sys.executable, str(AICJ), "uninstall", "--home", str(home)],
        capture_output=True,
        text=True,
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
