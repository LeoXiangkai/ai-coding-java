# Transaction, Async, And Idempotency Rule

Use for Service write flows, multi-table writes, async tasks, scheduled jobs, MQ/HTTP callbacks, cache writes, and retryable operations.

## P0

1. Multi-table writes must use `@Transactional(rollbackFor = Exception.class)` or an equivalent verified project transaction mechanism.
2. `@Transactional` and `@Async` must be called through Spring Bean proxy, not same-class self invocation.
3. Controller must not own transaction boundaries.
4. Write flows must preserve project data isolation.

## P1

1. Avoid HTTP, MQ send, file upload, and large loops inside a DB transaction unless explicitly justified.
2. Retryable operations need idempotency keys, unique constraints, status guards, or another verified duplicate-control mechanism.
3. Scheduled jobs in multi-node deployments need single-node routing, distributed lock, or proof that repeated execution is safe.
4. Cache writes must document DB/cache order, consistency window, and failure handling.
5. Batch jobs need chunking, retry, partial failure, and resume semantics.

## Review Questions

1. What data changes are atomic?
2. What happens after an exception?
3. What happens if the request/job/message is repeated?
4. What happens if cache or external service update fails after DB commit?

