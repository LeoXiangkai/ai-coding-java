# TAP Fullstack Collaboration

TAP is useful when a fullstack task spans independent frontend and backend repositories and multiple agents need an auditable, shared communication channel. This component treats TAP as an optional target-project harness, not as a default Java rule.

Observed reference shape: `@hua-labs/tap` v0.6.1 with one shared comms directory under the system root and one TAP state directory per repository.

## When To Use

Use this guide when all are true:

1. The task crosses at least two repositories, such as web and server.
2. Agents need to exchange API contracts, blockers, seed data, or closeout notes.
3. Messages must remain available even when the other runtime is idle.

Do not use TAP for single-agent work, ordinary local verification, production deployment, or secret delivery.

## Recommended Shape

```text
<system-root>/
  .tap/
    TAP-STATE.md
    <channel>-comms/
      inbox/
      onboarding/
      receipts/
      handoffs/
      archive/
      findings/
      reviews/
      displayed-notifications/
  code/
    <server-repo>/
      tap-config.json
      .mcp.json
      .tap-comms/
        bin/codex-tap
        state.json
    <web-repo>/
      tap-config.json
      .mcp.json
      .tap-comms/
        bin/codex-tap
        state.json
```

The shared comms directory is the only channel source of truth. Repository-local `.tap-comms/` directories are runtime state and logs.

## Initialize

From the ai-coding-java component repository:

```bash
python3 scripts/init_tap_fullstack.py /path/to/system-root \
  --channel-name fullstack \
  --repo server=/path/to/system-root/code/server:cc_server_agent \
  --repo web=/path/to/system-root/code/web:cc_web_agent
```

The script writes:

1. `<system-root>/.tap/TAP-STATE.md`
2. `<system-root>/.tap/<channel>-comms/onboarding/welcome.md`
3. `<system-root>/.tap/<channel>-comms/onboarding/sync-tap-pending.md`
4. `<system-root>/.tap/<channel>-comms/onboarding/sync-tap-pending.config.<agent>.json`
5. `<repo>/tap-config.json`
6. `<repo>/.mcp.json`
7. `<repo>/.tap-comms/bin/codex-tap`
8. `<repo>/.claude/skills/sync-tap-pending/SKILL.md`

It does not run `tap doctor --fix`, does not edit global Codex config, and does not write secrets.

## Runtime Rules

Claude Code can use repository `.mcp.json` directly. Start a new session and run the TAP warmup/list-unread flow provided by TAP.

Codex should use the repository wrapper when bridge/app-server mode is needed:

```bash
./.tap-comms/bin/codex-tap mcp list
npx @hua-labs/tap bridge start codex-<agent-name> --agent-name <agent-name>
```

Prefer wrapper injection over global `~/.codex/config.toml` TAP tables. Global injection can make every Codex project load a TAP server that points at the wrong system.

## Operating Discipline

1. Start each session by listing unread TAP messages without marking them read.
2. Send read receipts after consuming a message.
3. Treat machine-readable contracts as the source of truth, such as OpenAPI output or generated type declarations. Markdown messages should explain meaning, risk, and decisions.
4. Batch non-urgent open items through `sync-tap-pending`; do not send empty reminders.
5. For urgent blockers, send TAP and also tell the human owner. TAP delivery to the inbox does not mean the other agent has seen it in context.
6. Keep `.tap/`, `.tap-comms/`, logs, receipts, and secrets out of business repositories unless the target project explicitly decides otherwise.
7. When syncing pending items, handle unread counterpart requests first, then collect new requests from sent TAP threads and document anchors.
8. Do not resend the same pending item. A sent item remains valid until answered or withdrawn.
9. Configure document anchors by meaning, not by mechanically swapping frontend/backend configs. Mark anchors as `sendable`, `self-check`, or `human-only`.

## Verification

Use these checks before claiming TAP is ready:

```bash
npx @hua-labs/tap doctor --json
npx @hua-labs/tap comms-doctor --all-known --json
./.tap-comms/bin/codex-tap mcp list
```

If using the zero-global-pollution wrapper pattern, `tap doctor` may warn that the Codex global MCP table is missing. That is expected when wrapper injection is intentional. Record the warning and verify wrapper `mcp list` instead.

## Known Boundaries

1. TAP message persistence is reliable at the shared inbox level, but idle sessions may not receive messages in their conversation context automatically.
2. Codex bridge startup can require a real TTY depending on the local Codex runtime.
3. Model-provider authorization failures are not TAP failures. Verify Codex can run a minimal turn through the selected provider before blaming TAP.
4. Do not put plaintext credentials in `.mcp.json`, `tap-config.json`, wrapper scripts, TAP messages, or state notes.
