#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import json
import os
import shutil
import stat
import sys


DEFAULT_TAP_PACKAGE = "@hua-labs/tap"


@dataclass(frozen=True)
class RepoSpec:
    label: str
    path: Path
    agent: str
    runtime: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize an optional TAP fullstack collaboration harness for multi-repository target projects."
    )
    parser.add_argument("system_root", help="System root that owns the shared .tap directory")
    parser.add_argument(
        "--channel-name",
        required=True,
        help="Stable TAP channel name, for example fullstack",
    )
    parser.add_argument(
        "--repo",
        action="append",
        required=True,
        metavar="LABEL=PATH:AGENT[:RUNTIME]",
        help="Repository participant. Example: server=/workspace/code/server:cc_server_agent:claude",
    )
    parser.add_argument(
        "--tap-package",
        default=DEFAULT_TAP_PACKAGE,
        help="npm TAP package launcher. Defaults to @hua-labs/tap.",
    )
    parser.add_argument(
        "--codex-bin",
        default=shutil.which("codex") or "codex",
        help="Codex binary used by generated .tap-comms/bin/codex-tap wrappers.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing generated TAP files")
    return parser.parse_args()


def parse_repo(raw: str, system_root: Path) -> RepoSpec:
    if "=" not in raw:
        raise ValueError(f"--repo must use LABEL=PATH:AGENT[:RUNTIME], got {raw!r}")
    label, rest = raw.split("=", 1)
    parts = rest.rsplit(":", 2)
    if len(parts) == 2:
        path_text, agent = parts
        runtime = "claude"
    elif len(parts) == 3:
        path_text, agent, runtime = parts
    else:
        raise ValueError(f"--repo must include PATH and AGENT, got {raw!r}")

    label = label.strip()
    agent = agent.strip()
    runtime = runtime.strip().lower()
    if not label or not agent:
        raise ValueError(f"--repo label and agent are required, got {raw!r}")
    if runtime not in {"claude", "codex", "mixed"}:
        raise ValueError(f"--repo runtime must be claude, codex, or mixed, got {runtime!r}")

    repo_path = Path(path_text).expanduser()
    if not repo_path.is_absolute():
        repo_path = system_root / repo_path
    return RepoSpec(label=label, path=repo_path.resolve(), agent=agent, runtime=runtime)


def write_text(path: Path, text: str, force: bool) -> None:
    if path.exists() and not force:
        print(f"SKIP exists {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"OK wrote {path}")


def write_json(path: Path, payload: dict, force: bool) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    write_text(path, text, force)


def rel_from_repo(repo: Path, target: Path) -> str:
    return os.path.relpath(target, repo)


def codex_wrapper(codex_bin: str, tap_package: str, comms_dir: Path, repo: RepoSpec) -> str:
    return f"""#!/bin/sh
# TAP runtimeCommand wrapper. It injects TAP MCP for this repository only,
# avoiding a global ~/.codex/config.toml MCP table that can leak across projects.
exec "{codex_bin}" \\
  -c 'mcp_servers.tap.command="npx"' \\
  -c 'mcp_servers.tap.args=["{tap_package}","serve"]' \\
  -c 'mcp_servers.tap.approval_mode="auto"' \\
  -c 'mcp_servers.tap.env.TAP_COMMS_DIR="{comms_dir}"' \\
  -c 'mcp_servers.tap.env.TAP_STATE_DIR="{repo.path / ".tap-comms"}"' \\
  -c 'mcp_servers.tap.env.TAP_REPO_ROOT="{repo.path}"' \\
  -c "mcp_servers.tap.env.TAP_AGENT_NAME=\\"${{TAP_AGENT_NAME:-{repo.agent}}}\\"" \\
  "$@"
"""


def mcp_config(tap_package: str, comms_dir: Path, repo: RepoSpec) -> dict:
    return {
        "mcpServers": {
            "tap": {
                "type": "stdio",
                "command": "npx",
                "args": [tap_package, "serve"],
                "cwd": str(repo.path),
                "env": {
                    "TAP_AGENT_NAME": repo.agent,
                    "TAP_COMMS_DIR": str(comms_dir),
                    "TAP_STATE_DIR": str(repo.path / ".tap-comms"),
                    "TAP_REPO_ROOT": str(repo.path),
                    "TAP_CHANNEL_LOG_PATH": str(repo.path / ".tap-comms" / "logs" / "tap-mcp.log"),
                    "TAP_CLAUDE_CHANNEL_PUSH": "1",
                },
                "managedBy": "ai-coding-java",
                "schemaVersion": "setup-mcp-v0",
            }
        }
    }


def tap_config(comms_dir: Path, repo: RepoSpec) -> dict:
    return {
        "commsDir": rel_from_repo(repo.path, comms_dir),
        "runtimeCommand": str(repo.path / ".tap-comms" / "bin" / "codex-tap"),
    }


def tap_state(channel: str, tap_package: str, system_root: Path, comms_dir: Path, repos: list[RepoSpec]) -> str:
    rows = "\n".join(
        f"| {repo.label} | `{repo.path}` | `{repo.agent}` | {repo.runtime} |" for repo in repos
    )
    return f"""# TAP State

> Generated by ai-coding-java. Keep this file free of secrets and long logs.

## Channel

- Channel name: `{channel}`
- Shared comms directory: `{comms_dir}`
- TAP package: `{tap_package}`
- System root: `{system_root}`

## Repositories

| Label | Repository | Agent | Runtime |
|---|---|---|---|
{rows}

## Verification

Run from a participating repository:

```bash
npx {tap_package} doctor --json
npx {tap_package} comms-doctor --all-known --json
./.tap-comms/bin/codex-tap mcp list
```

If Codex uses wrapper injection, a missing global Codex TAP MCP table is expected. Verify the wrapper instead of running a global fix.

## Operating Notes

1. Start sessions by listing unread messages.
2. Send read receipts after consuming messages.
3. Use TAP for cross-repository contracts, blockers, seed data, and closeout notes.
4. Do not send secrets through TAP.
5. Urgent blockers still need human follow-up because inbox delivery does not guarantee context injection.
"""


def welcome(channel: str, repos: list[RepoSpec]) -> str:
    rows = "\n".join(f"| `{repo.agent}` | `{repo.label}` | `{repo.path}` |" for repo in repos)
    return f"""# {channel} TAP Channel

This channel is for cross-repository agent collaboration.

## Members

| Agent | Label | Repository |
|---|---|---|
{rows}

## Rules

1. List unread messages at session start.
2. Send a receipt after reading actionable messages.
3. Keep machine-readable API contracts in generated artifacts such as OpenAPI or type files; TAP messages explain meaning, risk, and decisions.
4. Batch non-urgent unresolved items with `sync-tap-pending`.
5. Do not put credentials, tokens, passwords, or sensitive logs in TAP.
6. TAP inbox delivery does not guarantee the other agent has seen the message in its conversation context.
"""


def sync_pending() -> str:
    return """# sync-tap-pending

Use this shared onboarding process to batch unresolved cross-agent questions.

## Config

Read `sync-tap-pending.config.<agent>.json` from this directory.

Each `docAnchors` item should state its semantic role:

1. `sendable`: items this agent needs from the counterpart.
2. `self-check`: items this agent owns; use for answering status questions or human reporting.
3. `human-only`: product, security, priority, or business-rule decisions that the counterpart cannot decide.

Do not mechanically swap `self` and `counterpart` and reuse the same anchors. First ask what each heading means: who owes whom.

## Source 0: Unread Inbox

Run this first. List unread TAP messages without marking them read and find counterpart requests that are waiting on this agent.

For each request:

1. If code, data, docs, or command output can answer it, gather evidence and include an answer.
2. If it requires this agent to perform an action, perform it first and then answer with the result.
3. If it requires a human or product decision, do not invent an answer; report it to the human owner.

Answers need a source pointer such as `file:line`, query output, or command output.

## Source A: Sent TAP Threads

Read recent inbox files sent by `self` to `counterpart`. Extract requests that ask the counterpart to confirm, provide, execute, or decide something.

Drop requests that were answered, withdrawn, superseded, or already sent in a previous pending handoff.

## Source B: Document Anchors

Read configured document anchors relative to the current repository root. Collect open items only when the anchor role is `sendable`.

Use `self-check` anchors for local status reporting. Use `human-only` anchors only for human-owner reporting.

## No Repeat Rule

Already sent pending items remain valid until answered or withdrawn. Do not resend the same item just because time passed or the counterpart is inactive.

Only send a new item when its content materially changed, such as new context, changed conclusion, or an escalation from non-blocking to blocking.

## Send Decision

| New pending | Waiting on self | Action |
|---|---|---|
| no | no | Do not send; report nothing pending. |
| yes | no | Send pending-item sync. |
| no | yes | Send answers. |
| yes | yes | Send one message: answers first, pending items second. |

Do not send empty messages. Do not suppress answers just because this agent has no new questions.

## Message Format

```markdown
# <Answers / Pending Items Sync / Answers + Pending Items Sync> (<self> -> <counterpart>)

## 0. Answers To Your Pending Items

### 1. <counterpart request>
- Source: `tap:<message>` section
- Conclusion:
- Evidence: `file:line` / query output / command output
- Executed: <only when an action was performed>

## 1. Needs Answer

### 1. <question>
- Source: `tap:<message>` or `doc:<file>:<line>`
- Context:
- Needed:
- Blocking:

## 2. Needs Action

Same structure.

## 3. FYI

Short bullets only.
```

## After Sending

1. Write sent items to `<commsDir>/handoffs/pending-<self>-to-<counterpart>.md`.
2. Send TAP read receipts only for counterpart messages that were actually answered.
3. Do not receipt unanswered or human-routed items.
4. Report to the human owner what was sent, what was skipped, and why.
"""


def sync_config(repo: RepoSpec, repos: list[RepoSpec], comms_dir: Path) -> dict:
    counterparts = [other.agent for other in repos if other.agent != repo.agent]
    return {
        "_comment": "Generated by ai-coding-java. Adjust docAnchors for project-specific contract or blocker documents.",
        "self": repo.agent,
        "counterpart": counterparts[0] if counterparts else "",
        "commsDir": str(comms_dir),
        "docAnchors": [
            {
                "file": "docs/contract-alignment.md",
                "heading": "Pending",
                "role": "sendable",
                "_why": "Replace with a real project document and heading when this agent needs the counterpart to answer or act.",
            },
            {
                "file": "docs/contract-alignment.md",
                "heading": "Owned By This Agent",
                "role": "self-check",
                "_why": "Use for local status answers and human reports. Do not send these as requests to the counterpart.",
            },
            {
                "file": "docs/contract-alignment.md",
                "heading": "Needs Human Decision",
                "role": "human-only",
                "_why": "Use for product, security, priority, or business-rule decisions that the counterpart agent cannot decide.",
            }
        ],
        "_docAnchorsLesson": "Do not mechanically swap self/counterpart configs. Decide each anchor by asking who owes whom.",
        "humanOnlyKeywords": ["product decision", "human decision", "security approval", "credential"],
    }


def claude_skill_shell(repo: RepoSpec, comms_dir: Path) -> str:
    process_path = comms_dir / "onboarding" / "sync-tap-pending.md"
    config_name = f"sync-tap-pending.config.{repo.agent}.json"
    return f"""---
name: sync-tap-pending
description: Batch current cross-agent pending items and send them through TAP. Use for pending sync, ask counterpart, sync-tap-pending, or collecting unresolved frontend/backend questions. Do not use for one-off questions; use TAP reply directly.
---

# sync-tap-pending shell

The process body lives in the shared TAP comms onboarding directory, not in this repository-local shell.

## Steps

1. Read the shared process:
   `{process_path}`
2. Read this agent's config from the same directory:
   `{config_name}`
3. Execute the shared process exactly. Do not rely on this shell as the process source; the shared file may change.

## Identity

Self: `{repo.agent}`
Repository: `{repo.path}`
"""


def ensure_repo(repo: RepoSpec) -> None:
    if not repo.path.exists() or not repo.path.is_dir():
        raise FileNotFoundError(f"repository path does not exist: {repo.path}")


def main() -> int:
    args = parse_args()
    system_root = Path(args.system_root).expanduser().resolve()
    if not system_root.exists() or not system_root.is_dir():
        print(f"FAIL system root does not exist: {system_root}", file=sys.stderr)
        return 1

    try:
        repos = [parse_repo(raw, system_root) for raw in args.repo]
        if len(repos) < 2:
            raise ValueError("at least two --repo participants are required")
        labels = {repo.label for repo in repos}
        agents = {repo.agent for repo in repos}
        if len(labels) != len(repos):
            raise ValueError("repo labels must be unique")
        if len(agents) != len(repos):
            raise ValueError("agent names must be unique")
        for repo in repos:
            ensure_repo(repo)
    except Exception as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    comms_dir = system_root / ".tap" / f"{args.channel_name}-comms"
    for subdir in [
        "inbox",
        "onboarding",
        "receipts",
        "handoffs",
        "archive",
        "findings",
        "reviews",
        "displayed-notifications/markers",
    ]:
        (comms_dir / subdir).mkdir(parents=True, exist_ok=True)
    for subdir in ["global-state/pids", "global-state/logs"]:
        (system_root / ".tap" / subdir).mkdir(parents=True, exist_ok=True)

    write_text(system_root / ".tap" / "TAP-STATE.md", tap_state(args.channel_name, args.tap_package, system_root, comms_dir, repos), args.force)
    write_text(comms_dir / "onboarding" / "welcome.md", welcome(args.channel_name, repos), args.force)
    write_text(comms_dir / "onboarding" / "sync-tap-pending.md", sync_pending(), args.force)

    for repo in repos:
        for subdir in ["pids", "logs", "secrets"]:
            (repo.path / ".tap-comms" / subdir).mkdir(parents=True, exist_ok=True)
        write_json(comms_dir / "onboarding" / f"sync-tap-pending.config.{repo.agent}.json", sync_config(repo, repos, comms_dir), args.force)
        write_json(repo.path / "tap-config.json", tap_config(comms_dir, repo), args.force)
        write_json(repo.path / ".mcp.json", mcp_config(args.tap_package, comms_dir, repo), args.force)
        wrapper_path = repo.path / ".tap-comms" / "bin" / "codex-tap"
        write_text(wrapper_path, codex_wrapper(args.codex_bin, args.tap_package, comms_dir, repo), args.force)
        if wrapper_path.exists():
            wrapper_path.chmod(wrapper_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            print(f"OK executable {wrapper_path}")
        write_text(repo.path / ".claude" / "skills" / "sync-tap-pending" / "SKILL.md", claude_skill_shell(repo, comms_dir), args.force)

    print("\nNext steps:")
    print("1. Review .tap/TAP-STATE.md and onboarding files; fill project-specific doc anchors.")
    print("2. Add .tap/, .tap-comms/, and TAP secrets/logs to the target project ignore policy unless explicitly committed.")
    print(f"3. Run: npx {args.tap_package} doctor --json")
    print(f"4. Run: npx {args.tap_package} comms-doctor --all-known --json")
    print("5. Run from each repo: ./.tap-comms/bin/codex-tap mcp list")
    print("6. For urgent blockers, notify the human owner as well as sending TAP.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
