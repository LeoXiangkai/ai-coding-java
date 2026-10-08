from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[3] / "core" / "skills" / "qa-testcase-pro" / "scripts" / "generate_xlsx.py"


def sample_input(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "project": "sample",
                "test_cases": [{"id": "TC-001", "title": "observable result"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_missing_openpyxl_returns_exit_two_with_actionable_message(tmp_path: Path) -> None:
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    script = isolated / "generate_xlsx.py"
    shutil.copy2(SCRIPT, script)
    (isolated / "openpyxl.py").write_text(
        "raise ImportError('blocked by fixture')\n", encoding="utf-8"
    )
    source = isolated / "input.json"
    sample_input(source)

    result = subprocess.run(
        [sys.executable, "-I", str(script), "--input", str(source), "--output", str(isolated / "out.xlsx")],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "openpyxl is required" in result.stderr
    assert "Markdown/CSV" in result.stderr


def test_with_openpyxl_generates_file_when_dependency_is_available(tmp_path: Path) -> None:
    pytest.importorskip("openpyxl", reason="openpyxl is not installed in this environment")
    source = tmp_path / "input.json"
    output = tmp_path / "out.xlsx"
    sample_input(source)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(source), "--output", str(output)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert output.is_file()
    assert output.stat().st_size > 0
