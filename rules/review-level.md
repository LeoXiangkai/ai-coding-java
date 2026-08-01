# Review Level Rule

Use for AI review, self-review, and pre-delivery checks.

## Levels

```text
P0: blocks delivery.
P1: should be fixed before delivery unless explicitly waived.
P2: suggestion; record but do not block.
```

## P0 Examples

1. Secret exposure.
2. SQL injection.
3. Missing data isolation condition.
4. Multi-table write without transaction.
5. Unverified destructive data operation.
6. False verification claim.

## P1 Examples

1. Missing core regression test.
2. Controller contains complex business logic.
3. Mapper SQL has realistic performance risk.
4. API field change lacks compatibility or curl evidence.
5. Async/retry flow lacks idempotency.

## Output

Use `templates/ai-review-template.md` or `docs/review-output-template.md`.

