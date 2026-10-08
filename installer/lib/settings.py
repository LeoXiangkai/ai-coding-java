from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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

    def to_dict(self, target: str) -> dict:
        return {
            "event": self.event,
            "matcher": self.matcher,
            "command": self.command,
            "target": target,
        }


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
            if isinstance(hook, dict) and hook.get("command") == key.command:
                return True
    return False


def merge_hooks(payload: dict, keys: list[HookKey]) -> list[HookKey]:
    added: list[HookKey] = []
    for key in keys:
        if HOOK_PATH_MARK not in key.command:
            raise UserError(f"hook command must contain {HOOK_PATH_MARK}: {key.command}")
        if has_hook(payload, key):
            continue
        container = payload.setdefault("hooks", {})
        if not isinstance(container, dict):
            raise UserError("hooks key must be an object")
        groups = container.setdefault(key.event, [])
        if not isinstance(groups, list):
            raise UserError(f"hooks.{key.event} must be a list")
        entry = {"hooks": [{"type": "command", "command": key.command}]}
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
                    and hook.get("command") == key.command
                    and HOOK_PATH_MARK in str(hook.get("command", ""))
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
