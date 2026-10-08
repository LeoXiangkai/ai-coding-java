from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .util import UserError, read_json

CATEGORIES = ("rules", "refs", "agents", "skills", "hooks", "bin", "templates")
CLAUDE_DIR = ".claude"
HOOK_DIR = "hooks/aicj"


@dataclass(frozen=True)
class FileItem:
    category: str
    source: Path
    target: str


@dataclass(frozen=True)
class HookItem:
    event: str
    matcher: str
    script: str
    blocking: bool


@dataclass
class ComponentIndex:
    files: list[FileItem] = field(default_factory=list)
    hooks: list[HookItem] = field(default_factory=list)
    packs: list[str] = field(default_factory=list)
    adapters: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _manifest_path(base: Path, kind: str, name: str | None = None) -> Path | None:
    if kind == "core":
        return base / "core" / "manifest.json"
    if kind == "pack":
        return base / "packs" / name / "pack.json"
    if kind == "adapter":
        return base / "adapters" / name / "adapter.json"
    if kind == "plugin":
        return base / "adapters" / "optional-plugins" / name / "plugin.json"
    return None


def _read_component(path: Path) -> tuple[list[FileItem], list[HookItem]]:
    data = read_json(path)
    if not isinstance(data, dict):
        raise UserError(f"{path}: top level must be an object")
    entries = data.get("entries", {})
    if not isinstance(entries, dict):
        raise UserError(f"{path}: entries must be an object")
    hooks_raw = data.get("hooks", [])
    if not isinstance(hooks_raw, list):
        raise UserError(f"{path}: hooks must be a list")

    root = path.parent
    items: list[FileItem] = []
    for category in CATEGORIES:
        rows = entries.get(category, [])
        if not isinstance(rows, list):
            raise UserError(f"{path}: entries.{category} must be a list")
        for row in rows:
            if not isinstance(row, dict):
                raise UserError(f"{path}: entries.{category} items must be objects")
            source = row.get("source")
            target = row.get("target")
            if not source or not target:
                raise UserError(f"{path}: entries.{category} needs source and target")
            items.extend(_expand(root, Path(source), _target(str(target), path), category))

    hooks: list[HookItem] = []
    for row in hooks_raw:
        if not isinstance(row, dict):
            raise UserError(f"{path}: hooks items must be objects")
        event = row.get("event")
        script = row.get("script")
        if not event or not script:
            raise UserError(f"{path}: hooks needs event and script")
        hooks.append(
            HookItem(
                event=str(event),
                matcher=str(row.get("matcher", "")),
                script=str(script),
                blocking=bool(row.get("blocking", False)),
            )
        )
    return items, hooks


def _target(raw: str, manifest_path: Path) -> str:
    rel = Path(raw.strip().lstrip("/"))
    if not raw.strip() or ".." in rel.parts:
        raise UserError(f"{manifest_path}: target must stay inside ~/.claude: {raw!r}")
    return f"{CLAUDE_DIR}/{rel.as_posix()}"


def _expand(root: Path, source: Path, target: str, category: str) -> list[FileItem]:
    full = root / source
    if not full.exists():
        raise UserError(f"component source missing: {full}")
    if full.is_file():
        return [FileItem(category=category, source=full, target=target)]
    out: list[FileItem] = []
    for child in sorted(full.rglob("*")):
        if not child.is_file():
            continue
        rel = child.relative_to(full).as_posix()
        out.append(FileItem(category=category, source=child, target=f"{target.rstrip('/')}/{rel}"))
    return out


def _detect_packs(cwd: Path) -> list[str]:
    found: list[str] = []
    if (cwd / "pom.xml").exists() or any(cwd.glob("build.gradle*")):
        found.append("java")
    if (cwd / "pyproject.toml").exists() or any(cwd.glob("requirements*.txt")) or (cwd / "setup.py").exists():
        found.append("python")
    if _has_vue_dep(cwd / "package.json"):
        found.append("vue")
    return found


def _has_vue_dep(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    for key in ("dependencies", "devDependencies"):
        section = data.get(key)
        if isinstance(section, dict) and "vue" in section:
            return True
    return False


def resolve_packs(requested: str, cwd: Path, available: list[str], global_install: bool) -> list[str]:
    if requested == "auto":
        detected = [name for name in _detect_packs(cwd) if name in available]
        if detected:
            return detected
        return list(available) if global_install else []
    return [part.strip() for part in requested.split(",") if part.strip()]


def available_names(base: Path, kind: str) -> list[str]:
    if kind == "pack":
        root = base / "packs"
        if not root.is_dir():
            return []
        return sorted(p.name for p in root.iterdir() if (p / "pack.json").is_file())
    names: list[str] = []
    adapters = base / "adapters"
    if adapters.is_dir():
        names.extend(sorted(p.name for p in adapters.iterdir() if (p / "adapter.json").is_file()))
    plugins = adapters / "optional-plugins"
    if plugins.is_dir():
        names.extend(sorted(p.name for p in plugins.iterdir() if (p / "plugin.json").is_file()))
    return names


def load_index(
    source_root: Path,
    packs: list[str],
    adapters: list[str],
) -> ComponentIndex:
    core_manifest = _manifest_path(source_root, "core")
    if core_manifest is None or not core_manifest.is_file():
        raise UserError(f"component manifest not found: {core_manifest}")

    index = ComponentIndex(packs=packs, adapters=adapters)
    components: list[tuple[Path | None, str]] = [(core_manifest, "core")]
    for name in packs:
        components.append((_manifest_path(source_root, "pack", name), f"pack {name}"))
    for name in adapters:
        adapter = _manifest_path(source_root, "adapter", name)
        plugin = _manifest_path(source_root, "plugin", name)
        if adapter and adapter.is_file():
            components.append((adapter, f"adapter {name}"))
        elif plugin and plugin.is_file():
            components.append((plugin, f"plugin {name}"))
        else:
            index.notes.append(f"{name}: no manifest -> no entries")

    for path, label in components:
        if path is None or not path.is_file():
            if label != "core":
                index.notes.append(f"{label}: no manifest -> no entries")
            continue
        items, hooks = _read_component(path)
        index.files.extend(items)
        index.hooks.extend(hooks)
    return index
