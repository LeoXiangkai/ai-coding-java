# Data Isolation Example: School And School Year

Type: project-rule-example

Scope: Education enrollment or school-scoped systems.

## Example Rule

Queries and writes that read school-scoped business data must preserve both school and school-year boundaries unless the project explicitly documents a cross-school or cross-year workflow.

## Verification Method

For changed SQL, Service filters, exports, imports, and sync tasks:

1. Identify the source of `schoolId` or equivalent school boundary.
2. Identify the source of `schoolYear` or annual context.
3. Confirm joins and updates do not drop either boundary.
4. For cross-school workflows, confirm the result shape explicitly labels source and target school semantics.

## Sanitization

This is a generic example. It does not contain real project data.

