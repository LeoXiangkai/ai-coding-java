# Java Layering Rule

Type: company-rule

Scope: Java enterprise projects using Controller / Service / Mapper layering.

## Reusable Fact

Controller receives and validates input, reads auth context, calls Service, and returns the project response type.

Service owns business orchestration, transaction boundaries, idempotency, state checks, and external adapter coordination.

Mapper/XML owns database access and must not become the place where complex business branching is hidden.

## Verification Method

Review changed files against:

1. Controller does not call Mapper directly.
2. Controller does not open transactions.
3. Service contains write transaction boundaries.
4. Mapper SQL preserves project data isolation.

## Applies When

The target project confirms a layered Java backend architecture.

## Does Not Apply When

The target project has a different verified architecture and its `AGENTS.md` documents the alternative.

