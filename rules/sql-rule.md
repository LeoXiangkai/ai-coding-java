# SQL And MyBatis Rule

Use for Mapper interfaces, MyBatis XML, SQL snippets, DDL/data scripts, and SQL-related review.

## P0

1. No SQL injection risk.
2. No unbounded update/delete without a business `where`.
3. No missing project data isolation condition, such as tenant, organization, school, year, or region.
4. No destructive production DDL without explicit target, backup/recovery plan, and approval.
5. No plaintext sensitive data persistence.

## P1

1. Avoid `select *`; select explicit columns.
2. Lists must page, limit, or justify bounded size.
3. Large or frequent queries must consider indexes.
4. Complex joins must describe main table, join fields, cardinality, and filter location.
5. One-to-many joins with pagination must verify result semantics.
6. Dynamic order/group/where fields must use whitelist mapping before `${}`.

## Verification

Standard SQL verification:

```text
compile
focused test when available
real dev/test data query or endpoint curl
explain when query shape or data volume is risky
```

If real data or local DB is unavailable, report `Not-tested` with the missing evidence.

