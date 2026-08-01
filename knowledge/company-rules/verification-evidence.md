# Verification Evidence Rule

Type: company-rule

Scope: All ai-coding-java target projects.

## Reusable Fact

Agents must report executed verification, not intended verification.

If a verification step cannot run because of environment, data, account, dependency, or time constraints, it must be reported as `Not-tested` with missing evidence and remaining risk.

## Verification Method

Delivery report must include:

1. Commands that actually ran.
2. Result summary.
3. Missing verification under `Not-tested`.
4. Remaining risk.

## Applies When

Every task claiming completion, fix, delivery readiness, release readiness, or review readiness.

