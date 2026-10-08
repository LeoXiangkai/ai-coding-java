from __future__ import annotations

import os
from pathlib import Path

from . import engine, manifest, mdblock, settings
from .util import UserError

PASS = "PASS"
WARN = "WARN"
MISSING = "MISSING"
SKIPPED = "SKIPPED"

THIRD_PARTY_SKILLS = (
    "grilling",
    "research",
    "prototype",
    "domain-modeling",
    "writing-for-agents",
)


def run_doctor(home: Path, source: Path | None = None) -> tuple[list[tuple[str, str, str]], int]:
    checks: list[tuple[str, str, str]] = []
    claude_dir = home / ".claude"
    if not claude_dir.is_dir():
        checks.append((MISSING, "home/.claude", str(claude_dir)))
        return checks, 1
    checks.append((PASS, "home/.claude", str(claude_dir)))

    loaded = _load_manifest(home, checks)
    if loaded is None:
        checks.extend(_third_party(home))
        return checks, 1 if any(status == MISSING for status, _n, _d in checks) else 0

    checks.extend(_entries(home, loaded))
    checks.extend(_md_block(home))
    checks.extend(_hooks(home, loaded))
    checks.extend(_bin_path(home, loaded))
    checks.extend(_codex(home, loaded))
    checks.extend(_third_party(home))

    missing = sum(1 for status, _name, _detail in checks if status == MISSING)
    return checks, 1 if missing else 0


def _load_manifest(home: Path, checks: list) -> manifest.Manifest | None:
    path = home / manifest.REL_PATH
    if not path.is_file():
        checks.append((MISSING, "manifest", f"{path} absent"))
        return None
    try:
        loaded = manifest.load(home)
    except UserError as exc:
        checks.append((MISSING, "manifest", str(exc)))
        return None
    checks.append((PASS, "manifest", f"{len(loaded.entries)} entries"))
    return loaded


def _entries(home: Path, loaded: manifest.Manifest) -> list[tuple[str, str, str]]:
    if not loaded.entries:
        return [(SKIPPED, "component entries", "no components installed")]
    out: list[tuple[str, str, str]] = []
    for entry in loaded.entries:
        if entry.kind == "md-block":
            continue
        target = home / entry.path
        if not target.exists() and not target.is_symlink():
            out.append((MISSING, entry.path, f"action={entry.action}"))
            continue
        if entry.sha256 and _current_digest(target) != entry.sha256:
            out.append((WARN, entry.path, "modified after install"))
            continue
        out.append((PASS, entry.path, f"action={entry.action}"))
    return out or [(SKIPPED, "component entries", "no file entries")]


def _current_digest(path: Path) -> str:
    try:
        return engine.digest(path)
    except OSError:
        return ""


def _md_block(home: Path) -> list[tuple[str, str, str]]:
    path = home / engine.CLAUDE_MD
    if not path.is_file():
        return [(MISSING, engine.CLAUDE_MD, "entry file absent")]
    text = path.read_text(encoding="utf-8")
    if not mdblock.has_block(text):
        return [(MISSING, engine.CLAUDE_MD, "marker block absent")]
    out = [(PASS, engine.CLAUDE_MD, "marker block present")]
    entry = home / ".claude" / engine.GLOBAL_REF
    if entry.is_file():
        out.append((PASS, engine.GLOBAL_REF, str(entry)))
    else:
        out.append((WARN, engine.GLOBAL_REF, "global entry file absent"))
    return out


def _hooks(home: Path, loaded: manifest.Manifest) -> list[tuple[str, str, str]]:
    if not loaded.settings_hooks:
        return [(SKIPPED, "settings hooks", "no hooks registered")]
    out: list[tuple[str, str, str]] = []
    grouped: dict[str, list[settings.HookKey]] = {}
    for row in loaded.settings_hooks:
        target = str(row.get("target", engine.SETTINGS))
        grouped.setdefault(target, []).append(
            settings.HookKey(str(row.get("event", "")), str(row.get("matcher", "")), str(row.get("command", "")))
        )
    for target, keys in sorted(grouped.items()):
        path = home / target
        try:
            payload = settings.load(path)
        except UserError as exc:
            out.append((MISSING, target, str(exc)))
            continue
        for key in keys:
            status = PASS if settings.has_hook(payload, key) else MISSING
            out.append((status, target, f"{key.event}|{key.matcher}"))
    return out


def _bin_path(home: Path, loaded: manifest.Manifest) -> list[tuple[str, str, str]]:
    bin_entries = [entry for entry in loaded.entries if entry.path.startswith(".claude/bin/")]
    if not bin_entries:
        return [(SKIPPED, "bin PATH", "no bin tools installed")]
    bin_dir = home / ".claude" / "bin"
    paths = [os.path.abspath(os.path.expanduser(p)) for p in os.environ.get("PATH", "").split(os.pathsep) if p]
    if os.path.abspath(str(bin_dir)) in paths:
        return [(PASS, "bin PATH", str(bin_dir))]
    return [(WARN, "bin PATH", f"{bin_dir} not on PATH")]


def _codex(home: Path, loaded: manifest.Manifest) -> list[tuple[str, str, str]]:
    if not (loaded.options.codex or loaded.options.codex_hooks):
        return [(SKIPPED, "codex", "not enabled")]
    out: list[tuple[str, str, str]] = []
    codex_dir = home / ".codex"
    if codex_dir.is_dir():
        out.append((PASS, "codex", str(codex_dir)))
    else:
        out.append((WARN, "codex", f"{codex_dir} absent"))
    if loaded.options.codex:
        links = [entry for entry in loaded.entries if entry.path.startswith(engine.CODEX_SKILLS + "/")]
        for entry in links:
            target = home / entry.path
            status = PASS if target.is_symlink() else WARN
            out.append((status, entry.path, "skill link"))
    return out


def _third_party(home: Path) -> list[tuple[str, str, str]]:
    root = home / ".agents" / "skills"
    out: list[tuple[str, str, str]] = []
    for name in THIRD_PARTY_SKILLS:
        if (root / name).exists():
            out.append((PASS, f"third-party skill {name}", str(root / name)))
        else:
            out.append((WARN, f"third-party skill {name}", f"not found under {root}; install manually if needed"))
    return out
