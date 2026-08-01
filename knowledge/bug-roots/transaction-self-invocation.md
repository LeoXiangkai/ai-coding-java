# Transaction Self Invocation

Type: bug-root

Scope: Spring projects using proxy-based `@Transactional`.

## Problem

`@Transactional` on a method does not take effect when the method is called through same-class self invocation.

## Reusable Fact

Proxy-sensitive annotations such as `@Transactional` and `@Async` must be invoked through the Spring container proxy.

## Verification Method

Review call path:

1. The transactional method is public or otherwise proxy-invokable according to project setup.
2. Caller obtains the target through Spring Bean injection or another verified proxy path.
3. Multi-table writes use `rollbackFor = Exception.class`.

## Applies When

Service methods use `@Transactional` or `@Async`.

