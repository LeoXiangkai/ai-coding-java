from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .util import UserError, abspath


def is_wsl() -> bool:
    if os.name == "nt":
        return False
    if os.environ.get("WSL_DISTRO_NAME", "").strip():
        return True
    try:
        release = Path("/proc/sys/kernel/osrelease").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    return "microsoft" in release.lower()


def _mount_root() -> Path:
    configured = os.environ.get("AICJ_WSL_MOUNT_ROOT", "").strip()
    return abspath(configured or "/mnt")


def windows_mount(path: str | Path) -> bool:
    resolved = abspath(path).resolve()
    root = _mount_root().resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError:
        return False
    parts = relative.parts
    return bool(parts and len(parts[0]) == 1 and parts[0].isalpha())


def wslpath_windows(path: Path) -> str:
    try:
        result = subprocess.run(
            ["wslpath", "-w", str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    except (OSError, UnicodeError, subprocess.SubprocessError) as exc:
        raise UserError(f"wslpath conversion failed for {path}: {exc}") from exc
    converted = result.stdout.strip()
    if result.returncode != 0 or not converted:
        detail = result.stderr.strip() or f"exit code {result.returncode}"
        raise UserError(f"wslpath conversion failed for {path}: {detail}")
    return converted


def find_windows_python() -> tuple[str, list[str]] | None:
    for name, prefix in (("py.exe", ["-3"]), ("python.exe", [])):
        executable = shutil.which(name)
        if not executable:
            continue
        try:
            result = subprocess.run(
                [executable, *prefix, "-c", "import sys;print(sys.version_info[:2] >= (3, 9))"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
            )
        except (OSError, UnicodeError, subprocess.SubprocessError):
            continue
        if result.returncode == 0 and result.stdout.strip() == "True":
            return executable, prefix
    return None


def windows_python_missing_error() -> UserError:
    return UserError(
        "WSL detected a Windows target, but no usable Windows Python 3.9+ was found. "
        "Install Python 3 in Windows (python.org or `winget install Python.Python.3.12`) and retry; "
        "or run `py -3 installer/aicj.py ...` from a Windows terminal."
    )
