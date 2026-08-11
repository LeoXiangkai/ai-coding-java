# TAP State

> This file belongs outside business repositories when possible. Keep it free of secrets.

## Channel

- Channel name:
- Shared comms directory:
- TAP package:
- Initialized at:

## Repositories

| Label | Repository | Agent | Runtime |
|---|---|---|---|
| server | `<path>` | `<agent>` | claude/codex |
| web | `<path>` | `<agent>` | claude/codex |

## Setup

Each repository should have:

1. `tap-config.json` pointing to the shared comms directory.
2. `.mcp.json` for Claude Code MCP discovery.
3. `.tap-comms/bin/codex-tap` for Codex wrapper injection.
4. `.claude/skills/sync-tap-pending/SKILL.md` as a local slash-command shell that points to the shared onboarding process.

## Verification

```bash
npx @hua-labs/tap doctor --json
npx @hua-labs/tap comms-doctor --all-known --json
./.tap-comms/bin/codex-tap mcp list
```

## Notes

- Prefer repository wrapper injection over global Codex MCP config.
- If wrapper injection is intentional, a missing global Codex TAP MCP table is not a blocker.
- TAP inbox delivery does not guarantee the other agent has seen the message in context.
- `sync-tap-pending` should answer unread counterpart requests first and never resend unchanged pending items.
