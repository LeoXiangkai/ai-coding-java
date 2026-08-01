# Summary

- Fixed a Service write flow that updated two tables without a shared transaction.
- Added rollback behavior and regression verification.

# Verification

- mvn -Dtest=OrderWriteServiceTest test: passed
- mvn -DskipTests compile: passed

# Not-tested

- local curl was not executed because this example is a sanitized fixture

# Review

- P0: none after fix
- P1: none
- P2: consider adding a dedicated integration test later

