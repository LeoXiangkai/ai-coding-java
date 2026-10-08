from __future__ import annotations

import os
from pathlib import Path

from .util import sha256_file

CREATED = "created"
ADOPTED = "adopted"
ADOPTED_SYMLINK = "adopted-symlink"
SKIPPED = "skipped"
REPLACED = "replaced"
CONFLICT = "conflict"


def classify(source: Path, target: Path, link: bool) -> str:
    if target.is_symlink():
        return ADOPTED_SYMLINK if _same_link(target, source) else CONFLICT
    if not target.exists():
        return CREATED
    if target.is_dir() or link:
        return CONFLICT
    return ADOPTED if sha256_file(target) == sha256_file(source) else CONFLICT


def _same_link(target: Path, source: Path) -> bool:
    try:
        return os.path.realpath(target) == os.path.realpath(source)
    except OSError:
        return False
