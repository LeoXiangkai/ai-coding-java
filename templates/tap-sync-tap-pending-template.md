# sync-tap-pending

This shared onboarding document is the only live process body for batching cross-agent pending items. Repository-local slash-command skills should be shells that point back here instead of copying the process.

## Config

Read `sync-tap-pending.config.<agent>.json` from this directory.

Required fields:

1. `self`
2. `counterpart`
3. `commsDir`
4. `docAnchors`
5. `humanOnlyKeywords`

If the config for the current agent is missing, stop and ask the human owner. Do not borrow another agent's config.

Each `docAnchors` item should state its semantic role:

```json
{
  "file": "docs/contract-alignment.md",
  "heading": "Pending",
  "role": "sendable"
}
```

Roles:

1. `sendable`: items this agent needs from the counterpart.
2. `self-check`: items this agent owns; use for answering status questions or human reporting, not for sending as requests.
3. `human-only`: product, security, priority, or business-rule decisions that the counterpart agent cannot decide.

Do not mechanically swap `self` and `counterpart` and reuse the same anchors. First ask what each heading means: who owes whom.

## Source 0: Unread Inbox

Run this first. List unread TAP messages without marking them read and find counterpart requests that are waiting on this agent.

For each request:

1. If code, data, docs, or command output can answer it, gather evidence and include an answer.
2. If it requires this agent to perform an action, perform it first and then answer with the result.
3. If it requires a human or product decision, do not invent an answer; report it to the human owner.

Do not answer from memory without evidence. Answers need a source pointer such as `file:line`, query output, or command output.

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

Use two dimensions:

1. New pending items this agent needs from the counterpart.
2. Counterpart requests waiting for this agent's answer.

Decision table:

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
3. Do not receipt unanswered or human-routed items; leave them visible for the next run.
4. Report to the human owner what was sent, what was skipped, and why.
