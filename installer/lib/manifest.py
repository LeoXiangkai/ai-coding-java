from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath

from .util import UserError, iso_now, read_json, write_json

VERSION = 1
REL_PATH = ".claude/aicj/manifest.json"
IN_PROGRESS = "in-progress"
COMPLETE = "complete"
ALLOWED_ROOTS = (".claude", ".codex", ".agents")


@dataclass
class Options:
    packs: list[str] = field(default_factory=list)
    adapters: list[str] = field(default_factory=list)
    codex: bool = False
    codex_hooks: bool = False
    strict: bool = False
    link: bool = False
    on_conflict: str = "skip"
    project: str = ""


@dataclass
class Entry:
    path: str
    kind: str
    action: str
    sha256: str = ""
    backup: str = ""
    link: str = ""
    block: str = ""


def safe_rel(raw: str, what: str, allow_root: bool = False) -> str:
    """Manifest paths are relative to home and must stay under ~/.claude, ~/.codex or ~/.agents."""
    text = str(raw)
    if not text.strip() or PurePosixPath(text).is_absolute() or PureWindowsPath(text).anchor:
        raise UserError(f"manifest {what} must be a relative path: {text!r}")
    parts = PurePosixPath(text.replace("\\", "/")).parts
    if ".." in parts or "." in parts or parts[0] not in ALLOWED_ROOTS or (len(parts) < 2 and not allow_root):
        raise UserError(f"manifest {what} is outside the managed directories: {text!r}")
    return text


def _entry(item) -> Entry:
    if not isinstance(item, dict):
        raise UserError("manifest entries must be objects")
    path = item.get("path")
    if not path:
        raise UserError("manifest entry needs path")
    backup = str(item.get("backup", ""))
    return Entry(
        path=safe_rel(path, "entry path"),
        kind=str(item.get("kind", "file")),
        action=str(item.get("action", "")),
        sha256=str(item.get("sha256", "")),
        backup=safe_rel(backup, "backup path") if backup else "",
        link=str(item.get("link", "")),
        block=str(item.get("block", "")),
    )


@dataclass
class Manifest:
    source_repo: str = ""
    source_commit: str = ""
    installed_at: str = ""
    options: Options = field(default_factory=Options)
    entries: list[Entry] = field(default_factory=list)
    settings_hooks: list[dict] = field(default_factory=list)
    created_dirs: list[str] = field(default_factory=list)
    state: str = COMPLETE

    def to_dict(self) -> dict:
        return {
            "version": VERSION,
            "state": self.state,
            "source": {"repo": self.source_repo, "commit": self.source_commit},
            "installed_at": self.installed_at,
            "options": asdict(self.options),
            "entries": [asdict(entry) for entry in self.entries],
            "settings_hooks": list(self.settings_hooks),
            "created_dirs": list(self.created_dirs),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Manifest":
        if not isinstance(data, dict):
            raise UserError("manifest must be a JSON object")
        if data.get("version") != VERSION:
            raise UserError(f"unsupported manifest version: {data.get('version')!r} (expected {VERSION})")
        state = str(data.get("state", COMPLETE))
        if state not in (IN_PROGRESS, COMPLETE):
            raise UserError(f"unknown manifest state: {state!r}")
        source = data.get("source") or {}
        options = data.get("options") or {}
        entries = data.get("entries") or []
        hooks = data.get("settings_hooks") or []
        if not isinstance(entries, list) or not isinstance(hooks, list):
            raise UserError("manifest entries and settings_hooks must be lists")
        return cls(
            source_repo=str(source.get("repo", "")),
            source_commit=str(source.get("commit", "")),
            installed_at=str(data.get("installed_at", "")),
            options=Options(
                packs=[str(x) for x in options.get("packs", [])],
                adapters=[str(x) for x in options.get("adapters", [])],
                codex=bool(options.get("codex", False)),
                codex_hooks=bool(options.get("codex_hooks", False)),
                strict=bool(options.get("strict", False)),
                link=bool(options.get("link", False)),
                on_conflict=str(options.get("on_conflict", "skip")),
                project=str(options.get("project", "")),
            ),
            entries=[_entry(item) for item in entries],
            settings_hooks=[dict(hook) for hook in hooks],
            created_dirs=[safe_rel(str(x), "created dir", allow_root=True) for x in data.get("created_dirs") or []],
            state=state,
        )

    def save(self, home: Path) -> None:
        self.installed_at = self.installed_at or iso_now()
        write_json(home / REL_PATH, self.to_dict())


def load(home: Path) -> Manifest | None:
    path = home / REL_PATH
    if not path.exists():
        return None
    return Manifest.from_dict(read_json(path))


def remove(home: Path) -> None:
    (home / REL_PATH).unlink(missing_ok=True)
