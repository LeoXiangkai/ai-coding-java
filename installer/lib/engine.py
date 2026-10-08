from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from . import conflict, index, manifest, mdblock, settings
from .util import (
    UserError,
    atomic_write,
    atomic_write_text,
    git_commit,
    iso_now,
    prune_empty_dirs,
    sha256_file,
    sha256_text,
    timestamp,
)

GLOBAL_REF = "aicj/CLAUDE.global.md"
CLAUDE_MD = ".claude/CLAUDE.md"
SETTINGS = ".claude/settings.json"
CODEX_HOOKS = ".codex/hooks.json"
CODEX_SKILLS = ".agents/skills"
HOOK_PATH_TOKEN = settings.HOOK_PATH_TOKEN
OWNED_ACTIONS = (conflict.CREATED, conflict.REPLACED)


@dataclass
class Report:
    lines: list[tuple[str, str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add(self, verb: str, path: str, note: str = "") -> None:
        self.lines.append((verb, path, note))

    def note(self, text: str) -> None:
        self.notes.append(text)

    def warn(self, text: str) -> None:
        self.warnings.append(text)


def hook_command(hook: index.HookItem, home: Path, strict: bool) -> str:
    if not hook.script.replace("\\", "/").startswith("hooks/aicj/"):
        raise UserError(f"hook script must live under hooks/aicj/: {hook.script}")
    script = home / ".claude" / hook.script
    prefix = "AICJ_HOOK_MODE=block " if strict and hook.blocking else ""
    if script.suffix == ".py":
        return f"{prefix}python3 {script}"
    return f"{prefix}{script}"


def digest(path: Path) -> str:
    if path.is_dir():
        return sha256_text(os.path.realpath(path))
    return sha256_file(path)


def _write_item(item: index.FileItem, target: Path, link: bool) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if link:
        target.symlink_to(item.source)
        return
    atomic_write(target, item.source.read_bytes())
    target.chmod(item.source.stat().st_mode)


def _apply_file(
    item: index.FileItem,
    home: Path,
    options: manifest.Options,
    ts: str,
    dry_run: bool,
    report: Report,
    previous: manifest.Entry | None,
) -> manifest.Entry:
    target = home / item.target
    decision = conflict.classify(item.source, target, options.link)
    backup_rel = ""
    source_digest = sha256_file(item.source)
    owned = previous is not None and previous.action in OWNED_ACTIONS

    if decision == conflict.CONFLICT and owned and _unchanged(target, previous):
        decision = "updated"
    elif decision == conflict.CONFLICT:
        if options.on_conflict != "backup":
            report.add(conflict.SKIPPED, item.target, "content differs; rerun with --on-conflict backup")
            if owned:
                return previous
            return manifest.Entry(item.target, "file", conflict.SKIPPED, source_digest)
        backup_rel = f"{item.target}.aicj-bak-{ts}"
        if not dry_run:
            target.rename(home / backup_rel)
        decision = conflict.REPLACED

    if decision in (conflict.CREATED, conflict.REPLACED, "updated") and not dry_run:
        if decision == "updated":
            target.unlink()
        _write_item(item, target, options.link)

    kind = "symlink" if options.link or decision == conflict.ADOPTED_SYMLINK else "file"
    report.add(decision, item.target, f"backup {backup_rel}" if backup_rel else "")
    if decision == conflict.REPLACED or not owned:
        action = conflict.CREATED if decision == "updated" else decision
        return manifest.Entry(item.target, kind, action, source_digest, backup_rel)
    # keep ownership from the earlier install so uninstall still removes or restores it
    return manifest.Entry(item.target, kind, previous.action, source_digest, previous.backup)


def _unchanged(target: Path, previous: manifest.Entry) -> bool:
    try:
        return bool(previous.sha256) and digest(target) == previous.sha256
    except OSError:
        return False


def _merge_hook_file(
    rel: str,
    home: Path,
    payload: dict,
    keys: list[settings.HookKey],
    stale: list[settings.HookKey],
    ts: str,
    dry_run: bool,
    report: Report,
) -> list[dict]:
    path = home / rel
    removed = settings.unmerge_hooks(payload, stale)
    added = settings.merge_hooks(payload, keys)
    if (added or removed) and not dry_run:
        if path.exists():
            backup_rel = f"{rel}.aicj-bak-{ts}"
            shutil.copy2(path, home / backup_rel)
            report.add("backup", backup_rel)
        settings.save(path, payload)
        settings.load(path)
    for key in removed:
        report.add("unhook", rel, f"{key.event}|{key.matcher} (stale)")
    for key in added:
        report.add("hook", rel, f"{key.event}|{key.matcher}")
    for key in keys:
        if key not in added:
            report.add(conflict.ADOPTED, rel, f"{key.event}|{key.matcher}")
    return [key.to_dict(rel) for key in keys]


def _apply_md_block(
    home: Path, dry_run: bool, report: Report, previous: manifest.Entry | None
) -> manifest.Entry:
    path = home / CLAUDE_MD
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    block_digest = sha256_text(mdblock.build_block(GLOBAL_REF))
    if mdblock.has_block(text):
        action = previous.action if previous else conflict.ADOPTED
        report.add(conflict.ADOPTED, CLAUDE_MD, "marker block present")
        return manifest.Entry(CLAUDE_MD, "md-block", action, block_digest)
    if not dry_run:
        atomic_write_text(path, mdblock.append_block(text, GLOBAL_REF))
    report.add(conflict.CREATED, CLAUDE_MD, "marker block")
    return manifest.Entry(CLAUDE_MD, "md-block", conflict.CREATED, block_digest)


def _codex_skill_links(
    items: list[index.FileItem],
    home: Path,
    options: manifest.Options,
    ts: str,
    dry_run: bool,
    report: Report,
    previous: dict[str, manifest.Entry],
) -> list[manifest.Entry]:
    if not options.codex:
        return []
    names: list[str] = []
    for item in items:
        parts = Path(item.target).parts
        if len(parts) >= 3 and parts[0] == ".claude" and parts[1] == "skills" and parts[2] not in names:
            names.append(parts[2])

    out: list[manifest.Entry] = []
    for name in names:
        source = home / ".claude" / "skills" / name
        target = home / CODEX_SKILLS / name
        rel = f"{CODEX_SKILLS}/{name}"
        decision = conflict.classify(source, target, True)
        backup_rel = ""
        if decision == conflict.CONFLICT:
            if options.on_conflict != "backup":
                report.add(conflict.SKIPPED, rel, "codex skill link conflict")
                out.append(manifest.Entry(rel, "symlink", conflict.SKIPPED))
                continue
            backup_rel = f"{rel}.aicj-bak-{ts}"
            if not dry_run:
                target.rename(home / backup_rel)
            decision = conflict.REPLACED
        if decision in (conflict.CREATED, conflict.REPLACED) and not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(source)
        link_digest = sha256_text(os.path.realpath(source))
        report.add(decision, rel, "codex skill link")
        prev = previous.get(rel)
        if decision == conflict.ADOPTED_SYMLINK and prev is not None and prev.action in OWNED_ACTIONS:
            out.append(manifest.Entry(rel, "symlink", prev.action, link_digest, prev.backup))
        else:
            out.append(manifest.Entry(rel, "symlink", decision, link_digest, backup_rel))
    return out


def _hook_keys(rows: list[dict], target: str) -> list[settings.HookKey]:
    return [
        settings.HookKey(str(row.get("event", "")), str(row.get("matcher", "")), str(row.get("command", "")))
        for row in rows
        if str(row.get("target", SETTINGS)) == target
    ]


def run_install(
    home: Path,
    source: Path,
    options: manifest.Options,
    dry_run: bool,
) -> tuple[Report, manifest.Manifest]:
    report = Report()
    idx = index.load_index(source, options.packs, options.adapters)
    for note in idx.notes:
        report.note(note)

    old = manifest.load(home)
    previous = {entry.path: entry for entry in old.entries} if old else {}
    old_hooks = old.settings_hooks if old else []

    keys = [
        settings.HookKey(hook.event, hook.matcher, hook_command(hook, home, options.strict))
        for hook in idx.hooks
    ]
    hook_targets = [SETTINGS, CODEX_HOOKS] if options.codex_hooks else [SETTINGS]
    hook_targets += sorted({str(row.get("target", SETTINGS)) for row in old_hooks} - set(hook_targets))
    # parse every hook file before touching disk so invalid JSON aborts with nothing written
    payloads = {rel: settings.load(home / rel) for rel in hook_targets}

    ts = timestamp()
    entries = [
        _apply_file(item, home, options, ts, dry_run, report, previous.get(item.target))
        for item in idx.files
    ]
    entries.extend(_codex_skill_links(idx.files, home, options, ts, dry_run, report, previous))

    planned = {entry.path for entry in entries} | {CLAUDE_MD}
    for path, entry in previous.items():
        if path not in planned and entry.kind in ("file", "symlink") and entry.action in OWNED_ACTIONS:
            report.note(f"{path}: no longer shipped, kept and still tracked for uninstall")
            entries.append(entry)

    hooks: list[dict] = []
    for rel in hook_targets:
        wanted = keys if rel == SETTINGS or (rel == CODEX_HOOKS and options.codex_hooks) else []
        stale = [key for key in _hook_keys(old_hooks, rel) if key not in wanted]
        if not wanted and not stale:
            continue
        existed = (home / rel).exists()
        hooks += _merge_hook_file(rel, home, payloads[rel], wanted, stale, ts, dry_run, report)
        prev = previous.get(rel)
        action = prev.action if prev else (conflict.ADOPTED if existed else conflict.CREATED)
        entries.append(manifest.Entry(rel, "settings-hook", action))

    entries.append(_apply_md_block(home, dry_run, report, previous.get(CLAUDE_MD)))

    result = manifest.Manifest(
        source_repo=str(source),
        source_commit=git_commit(source),
        installed_at=iso_now(),
        options=options,
        entries=entries,
        settings_hooks=hooks,
    )
    if not dry_run:
        result.save(home)
        report.add("manifest", manifest.REL_PATH)
    return report, result


def _restore_or_remove(entry: manifest.Entry, home: Path, report: Report) -> None:
    target = home / entry.path
    if not target.exists() and not target.is_symlink():
        report.note(f"{entry.path}: already gone")
        return
    try:
        current = digest(target)
    except OSError:
        current = ""
    if entry.sha256 and current != entry.sha256:
        report.warn(f"{entry.path}: modified after install, kept")
        return
    if entry.action == conflict.REPLACED and entry.backup:
        backup = home / entry.backup
        if backup.exists() or backup.is_symlink():
            if target.is_symlink() or target.is_file():
                target.unlink()
            else:
                target.rmdir()
            os.replace(backup, target)
            report.add("restored", entry.path, f"from {entry.backup}")
            return
        report.warn(f"{entry.path}: backup {entry.backup} missing, removed without restore")
    if target.is_symlink() or target.is_file():
        target.unlink()
    else:
        target.rmdir()
    report.add("removed", entry.path)
    prune_empty_dirs(target.parent, home)


def _unmerge_hook_file(
    rel: str, home: Path, keys: list[settings.HookKey], report: Report, created: bool
) -> None:
    if not keys:
        return
    path = home / rel
    if not path.exists():
        report.note(f"{rel}: already gone")
        return
    payload = settings.load(path)
    removed = settings.unmerge_hooks(payload, keys)
    for key in removed:
        report.add("unhook", rel, f"{key.event}|{key.matcher}")
    if not removed:
        return
    if payload or not created:
        settings.save(path, payload)
        return
    path.unlink()
    prune_empty_dirs(path.parent, home)


def _remove_md_block(entry: manifest.Entry, home: Path, report: Report) -> None:
    path = home / entry.path
    if not path.exists():
        report.note(f"{entry.path}: already gone")
        return
    text = path.read_text(encoding="utf-8")
    rest, removed = mdblock.remove_block(text)
    if not removed:
        report.note(f"{entry.path}: marker block absent")
        return
    if rest.strip():
        atomic_write_text(path, rest)
    else:
        path.unlink()
        prune_empty_dirs(path.parent, home)
    report.add("removed", entry.path, "marker block")


def run_uninstall(home: Path, dry_run: bool) -> Report:
    report = Report()
    loaded = manifest.load(home)
    if loaded is None:
        report.note("no manifest; nothing installed")
        return report

    hook_keys: dict[str, list[settings.HookKey]] = {}
    for row in loaded.settings_hooks:
        target = str(row.get("target", SETTINGS))
        hook_keys.setdefault(target, []).append(
            settings.HookKey(str(row.get("event", "")), str(row.get("matcher", "")), str(row.get("command", "")))
        )

    created_hook_files = {
        entry.path
        for entry in loaded.entries
        if entry.kind == "settings-hook" and entry.action == conflict.CREATED
    }
    # reverse order: codex links point into installed skills and must go first
    for entry in reversed(loaded.entries):
        if entry.kind == "settings-hook":
            continue
        if entry.kind == "md-block":
            if dry_run:
                report.add("removed", entry.path, "marker block")
            else:
                _remove_md_block(entry, home, report)
        elif entry.action in (conflict.CREATED, conflict.REPLACED):
            if dry_run:
                report.add("removed", entry.path)
            else:
                _restore_or_remove(entry, home, report)
        else:
            report.add("kept", entry.path, entry.action)

    for target, keys in sorted(hook_keys.items()):
        if dry_run:
            for key in keys:
                report.add("unhook", target, f"{key.event}|{key.matcher}")
        else:
            _unmerge_hook_file(target, home, keys, report, target in created_hook_files)

    if dry_run:
        report.add("removed", manifest.REL_PATH)
    else:
        manifest.remove(home)
        report.add("removed", manifest.REL_PATH)
        prune_empty_dirs(home / ".claude" / "aicj", home)
    return report


def run_status(home: Path, source: Path | None) -> Report:
    report = Report()
    loaded = manifest.load(home)
    if loaded is None:
        report.note("not installed (no manifest)")
        return report

    root = source or (Path(loaded.source_repo) if loaded.source_repo else None)
    if root is None or not root.is_dir():
        report.note(f"source root unavailable: {root}")
        return report

    idx = index.load_index(root, loaded.options.packs, loaded.options.adapters)
    seen: set[str] = set()
    for item in idx.files:
        seen.add(item.target)
        target = home / item.target
        if not target.exists() and not target.is_symlink():
            report.add("missing", item.target, str(item.source))
            continue
        if conflict.classify(item.source, target, False) == conflict.ADOPTED:
            report.add("installed", item.target, str(item.source))
        else:
            report.add("differs", item.target, f"diff {item.source} {target}")
    for entry in loaded.entries:
        if entry.path in seen or entry.kind == "md-block":
            continue
        target = home / entry.path
        state = "installed" if target.exists() or target.is_symlink() else "missing"
        report.add(state, entry.path, entry.action)
    report.note(f"installed_at {loaded.installed_at}")
    report.note(f"options {loaded.options.packs} adapters={loaded.options.adapters}")
    return report
