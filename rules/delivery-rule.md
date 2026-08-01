# Delivery Rule

Use before reporting completion, release readiness, or handoff.

## Required Report

1. Changed files.
2. Impacted modules, APIs, tables, config, jobs, caches, and external systems.
3. Verification commands and results.
4. `Not-tested` items with reasons and remaining risk.
5. P0/P1/P2 review result.

## P0

1. Do not claim completion without executed verification or explicit `Not-tested`.
2. Do not hide failing tests, compile errors, startup errors, or curl failures.
3. Do not stage or commit unrelated user changes.

## P1

1. Prefer the narrowest verification proving the change.
2. Controller / VO / Mapper SQL changes should compile, start locally, and curl with dev/test data when feasible.
3. DDL/data scripts should apply to dev/test and verify post-state, except production.
4. Release notes should mention config switches, DB scripts, compatibility, and rollback when relevant.

