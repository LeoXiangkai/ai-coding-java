from __future__ import annotations

import json
import os
import posixpath
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .util import UserError, read_json

CATEGORIES = ("rules", "refs", "agents", "skills", "hooks", "bin", "templates")
CLAUDE_DIR = ".claude"
HOOK_DIR = "hooks/aicj"
# files the installer itself owns; a component entry must never target them
RESERVED_TARGETS = frozenset(
    {
        f"{CLAUDE_DIR}/settings.json",
        f"{CLAUDE_DIR}/claude.md",
        f"{CLAUDE_DIR}/aicj/manifest.json",
        f"{CLAUDE_DIR}/hooks.json",
    }
)


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
    optional: bool = False

    @property
    def name(self) -> str:
        """Registration name: script stem, e.g. hooks/aicj/git-safe-rewrite.py -> git-safe-rewrite."""
        return posixpath.basename(self.script).rsplit(".", 1)[0]


@dataclass
class ComponentIndex:
    files: list[FileItem] = field(default_factory=list)
    hooks: list[HookItem] = field(default_factory=list)
    packs: list[str] = field(default_factory=list)
    adapters: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    plugins: list["PluginRequirements"] = field(default_factory=list)


@dataclass(frozen=True)
class PluginRequirements:
    name: str
    commands: tuple[str, ...] = ()
    files: tuple[str, ...] = ()


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


def _read_component(path: Path, source_root: Path) -> tuple[list[FileItem], list[HookItem]]:
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
            items.extend(_expand(root, Path(source), _target(str(target), path), category, source_root))

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
                optional=bool(row.get("optional", False)),
            )
        )
    return items, hooks


def plugin_requirements(path: Path) -> PluginRequirements:
    data = read_json(path)
    raw = data.get("requires", {})
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise UserError(f"{path}: requires must be an object")

    def values(key: str) -> tuple[str, ...]:
        value = raw.get(key, [])
        if value is None:
            return ()
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise UserError(f"{path}: requires.{key} must be a list of strings")
        return tuple(item.strip() for item in value if item.strip())

    return PluginRequirements(path.parent.name, values("commands"), values("files"))


def missing_requirements(home: Path, requirements: PluginRequirements) -> list[str]:
    missing: list[str] = []
    for command in requirements.commands:
        if shutil.which(command) is None:
            missing.append(f"command {command}")
    claude_dir = home / CLAUDE_DIR
    for rel in requirements.files:
        path = Path(rel)
        if path.is_absolute() or ".." in path.parts:
            missing.append(f"file {rel} (invalid relative path)")
        elif not (claude_dir / path).exists():
            missing.append(f"file {rel}")
    return missing


def _target(raw: str, manifest_path: Path) -> str:
    rel = Path(raw.strip().lstrip("/"))
    if not raw.strip() or ".." in rel.parts:
        raise UserError(f"{manifest_path}: target must stay inside ~/.claude: {raw!r}")
    normalized = posixpath.normpath(rel.as_posix())
    if normalized in ("", "."):
        raise UserError(f"{manifest_path}: target must name a file or directory: {raw!r}")
    full = f"{CLAUDE_DIR}/{normalized}"
    if full.lower() in RESERVED_TARGETS:
        raise UserError(f"{manifest_path}: target {raw!r} is managed by the installer itself")
    return full


def _inside(path: Path, root: Path) -> bool:
    real = Path(os.path.realpath(path))
    base = Path(os.path.realpath(root))
    return real == base or base in real.parents


def _expand(root: Path, source: Path, target: str, category: str, source_root: Path) -> list[FileItem]:
    full = root / source
    if not full.exists():
        raise UserError(f"component source missing: {full}")
    if not _inside(full, source_root):
        raise UserError(f"component source resolves outside the component root: {full}")
    if full.is_file():
        if full.suffix in {".pyc", ".pyo"} or "__pycache__" in full.parts:
            return []
        return [FileItem(category=category, source=full, target=target)]
    out: list[FileItem] = []
    for child in sorted(full.rglob("*")):
        if (
            child.is_symlink()
            or not child.is_file()
            or not _inside(child, source_root)
            or "__pycache__" in child.parts
            or child.suffix in {".pyc", ".pyo"}
        ):
            continue
        rel = child.relative_to(full).as_posix()
        out.append(FileItem(category=category, source=child, target=f"{target.rstrip('/')}/{rel}"))
    return out


def _check_targets(items: list[FileItem]) -> None:
    seen: dict[str, str] = {}
    for item in items:
        key = item.target.lower()
        if key in RESERVED_TARGETS:
            raise UserError(f"target {item.target} is managed by the installer itself")
        if key in seen:
            raise UserError(f"duplicate install target {item.target} ({seen[key]} and {item.source})")
        seen[key] = str(item.source)
    for key in seen:
        parent = posixpath.dirname(key)
        while parent and parent != CLAUDE_DIR:
            if parent in seen:
                raise UserError(f"install target {key} sits below file target {parent}")
            parent = posixpath.dirname(parent)


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
        items, hooks = _read_component(path, source_root)
        index.files.extend(items)
        index.hooks.extend(hooks)
        if label.startswith("plugin "):
            index.plugins.append(plugin_requirements(path))
    _check_targets(index.files)
    return index
