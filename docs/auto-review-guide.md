# Auto Review Guide

This guide covers Phase 3: lightweight deterministic checks plus AI semantic review.

## Deterministic Checks

Use deterministic checks for issues that are cheap to detect:

```bash
python3 /path/to/ai-coding-java/scripts/static_review_check.py /path/to/target-project
```

Current checks:

1. P0 possible plaintext secrets.
2. P0 MyBatis `${}` requiring whitelist proof.
3. P0 update/delete statements that appear to lack `where`.
4. P1 `@Transactional` without `rollbackFor`.

The script is intentionally lightweight and may require human review for false positives. It does not install hooks or block commits by itself.

## AI Semantic Review

After deterministic checks, use `templates/ai-review-template.md` and review:

1. Whether layering is preserved.
2. Whether project business rules were bypassed.
3. Whether data isolation was preserved.
4. Whether transaction, async, cache, and idempotency boundaries are safe.
5. Whether verification evidence matches the real risk.

## Recommended Flow

```text
diff
  -> static_review_check.py
  -> rule-index routed AI review
  -> focused fixes
  -> verification matrix
  -> delivery report
```

## Exit Codes

```text
0: no deterministic P0/P1 findings
1: P1 findings only
2: at least one P0 finding
```

