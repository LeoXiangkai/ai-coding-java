# Requirements Checklist

Work ID:
Requirement brief:
Status: draft

Use this checklist only for complex, high-risk, or cross-module work. Small changes can skip it.

## Scope Clarity

- [ ] Goal is specific and testable.
- [ ] Non-goals are listed.
- [ ] User roles and main flow are clear.
- [ ] Compatibility constraints are clear.

## Acceptance

- [ ] Acceptance criteria use Given/When/Then where possible.
- [ ] Normal path is covered.
- [ ] Boundary conditions are covered.
- [ ] Failure path is covered.
- [ ] Regression scope is clear.

## Enterprise Java Risk

- [ ] Data boundary is clear, such as tenant, organization, school, year, or region.
- [ ] Permission and role impact is clear.
- [ ] API contract impact is clear.
- [ ] Table, SQL, or DDL impact is clear.
- [ ] Transaction, idempotency, async, cache, or external callback risk is clear.
- [ ] Config, job, file, or external system dependency is clear.

## Verification

- [ ] Required automated tests or compile checks are clear.
- [ ] Required manual or API verification is clear.
- [ ] Not-tested items are acceptable and documented.
- [ ] Release and rollback impact is understood.

## Open Questions

| Question | Owner | Needed Before |
|---|---|---|

## Decision

Proceed:
Reason:
Reviewer:
Date:
