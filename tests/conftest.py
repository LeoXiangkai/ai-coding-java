from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
AICJ = REPO / "installer" / "aicj.py"
FIXTURE = REPO / "tests" / "fixtures" / "fake-component"
SANITIZE = REPO / "scripts" / "sanitize_check.py"


def run_aicj(*args: str, home: Path, source: Path | None = FIXTURE) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(AICJ), *args, "--home", str(home)]
    if source is not None:
        cmd += ["--source", str(source)]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))


def run_sanitize(root: Path, extra: Path | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if extra is not None:
        env["AICJ_SANITIZE_EXTRA"] = str(extra)
    else:
        env.pop("AICJ_SANITIZE_EXTRA", None)
    return subprocess.run(
        [sys.executable, str(SANITIZE), "--root", str(root)],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        env=env,
    )


def snapshot(root: Path, ignore: tuple[str, ...] = ()) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if any(rel.startswith(prefix) for prefix in ignore):
            continue
        if path.is_symlink():
            out[rel] = "link:" + os.readlink(path)
        elif path.is_file():
            out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def files_under(root: Path) -> list[str]:
    return sorted(snapshot(root))


@pytest.fixture()
def home(tmp_path: Path) -> Path:
    target = tmp_path / "home"
    target.mkdir()
    return target
