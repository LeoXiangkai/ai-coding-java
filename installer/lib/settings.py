from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
import re

from .util import UserError, read_json, write_json

HOOK_PATH_MARK = "/hooks/aicj/"
# these events ignore matchers, so no matcher key is written for them
NO_MATCHER_EVENTS = frozenset(
    {"SessionStart", "Stop", "UserPromptSubmit", "SessionEnd", "PreCompact", "Notification"}
)


@dataclass(frozen=True)
class HookKey:
    event: str
    matcher: str
    command: str
    args: tuple[str, ...] = ()

    def to_dict(self, target: str) -> dict:
        return {
            "event": self.event,
            "matcher": self.matcher,
            "command": self.command,
            "args": list(self.args),
            "target": target,
        }


def _norm(value: object) -> str:
    text = str(value).replace("\\", "/")
    return text.casefold() if PureWindowsPath(text).drive else text


def _matches(hook: dict, key: HookKey) -> bool:
    return (hook.get("type") == "command" and _norm(hook.get("command", "")) == _norm(key.command)
            and tuple(_norm(arg) for arg in _hook_args(hook)) == tuple(_norm(arg) for arg in key.args))


def _owned(command: object, args: tuple[str, ...] | list[str] = ()) -> bool:
    return HOOK_PATH_MARK in _norm(command) or any(HOOK_PATH_MARK in _norm(arg) for arg in args)


def _script_path(command: object, args: tuple[str, ...] | list[str] = ()) -> str:
    """Extract and normalize the complete hook script path from exec or shell forms."""
    if args:
        values = [_norm(arg) for arg in args]
    else:
        # normalize per token: a leading interpreter word would hide the drive letter from _norm
        values = [_norm(match.group(0).strip('"\''))
                  for match in re.finditer(r'"[^"]*"|\'[^\']*\'|\S+', str(command).replace("\\", "/"))]
    for value in values:
        if HOOK_PATH_MARK in value:
            return value
    return ""


def _same_script(left: object, left_args: tuple[str, ...] | list[str], right: HookKey) -> bool:
    left_path = _script_path(left, left_args)
    right_path = _script_path(right.command, right.args)
    return bool(left_path and right_path) and left_path == right_path


def _hook_args(hook: object) -> tuple[str, ...]:
    raw = hook.get("args", ()) if isinstance(hook, dict) else getattr(hook, "args", ())
    if isinstance(raw, (list, tuple)):
        return tuple(str(item) for item in raw)
    return ()


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    data = read_json(path)
    if not isinstance(data, dict):
        raise UserError(f"{path}: top level must be a JSON object")
    return data


def _groups(payload: dict, event: str) -> list:
    container = payload.get("hooks")
    if container is None:
        return []
    if not isinstance(container, dict):
        raise UserError("hooks key must be an object")
    groups = container.get(event)
    if groups is None:
        return []
    if not isinstance(groups, list):
        raise UserError(f"hooks.{event} must be a list")
    return groups


def has_hook(payload: dict, key: HookKey) -> bool:
    for group in _groups(payload, key.event):
        if not isinstance(group, dict) or group.get("matcher", "") != key.matcher:
            continue
        for hook in group.get("hooks") or []:
            if (
                isinstance(hook, dict)
                and _matches(hook, key)
            ):
                return True
            if isinstance(hook, dict) and not _hook_args(hook) and len(key.args) == 1:
                if _same_script(hook.get("command", ""), (), key):
                    return True
    return False


def merge_hooks(payload: dict, keys: list[HookKey]) -> list[HookKey]:
    added: list[HookKey] = []
    for key in keys:
        if not _owned(key.command, key.args):
            raise UserError(f"hook command must contain {HOOK_PATH_MARK}: {key.command}")
        if has_hook(payload, key):
            continue
        container = payload.setdefault("hooks", {})
        if not isinstance(container, dict):
            raise UserError("hooks key must be an object")
        groups = container.setdefault(key.event, [])
        if not isinstance(groups, list):
            raise UserError(f"hooks.{key.event} must be a list")
        entry = {"hooks": [{"type": "command", "command": key.command, "args": list(key.args)}]}
        if key.event not in NO_MATCHER_EVENTS:
            entry = {"matcher": key.matcher, **entry}
        groups.append(entry)
        added.append(key)
    return added


def unmerge_hooks(payload: dict, keys: list[HookKey]) -> list[HookKey]:
    container = payload.get("hooks")
    if not isinstance(container, dict):
        return []
    removed: list[HookKey] = []
    for key in keys:
        groups = container.get(key.event)
        if not isinstance(groups, list):
            continue
        for group in list(groups):
            if not isinstance(group, dict) or group.get("matcher", "") != key.matcher:
                continue
            hooks = group.get("hooks")
            if not isinstance(hooks, list):
                continue
            kept = [
                hook
                for hook in hooks
                if not (
                    isinstance(hook, dict)
                    and (_matches(hook, key) or _same_script(hook.get("command", ""), _hook_args(hook), key))
                    and _owned(hook.get("command", ""), _hook_args(hook))
                )
            ]
            if len(kept) != len(hooks):
                removed.append(key)
                if kept:
                    group["hooks"] = kept
                else:
                    groups.remove(group)
        if not groups:
            container.pop(key.event, None)
    if not container:
        payload.pop("hooks", None)
    return removed


def save(path: Path, payload: dict) -> None:
    write_json(path, payload)
