# Java 8 / Spring Boot 2 / MyBatis Rule

Use this rule only when the target project confirms this stack. Do not force it onto Java 17, Spring Boot 3, Gradle-only, JPA, or non-MyBatis projects.

## P0

1. Do not introduce APIs unsupported by the confirmed project JDK.
2. Do not bypass existing project response, exception, auth, or tenant/school/year context helpers.
3. Do not add incompatible Spring Boot, MyBatis, or dependency versions without explicit architecture confirmation.

## P1

1. Controller should receive/validate parameters, read auth context, call Service, and return the project response type.
2. Service should own business orchestration, transaction boundaries, idempotency, and state checks.
3. Mapper/XML should own data access, not complex business branching.
4. Entity should represent table structure; external API should use request/response VO/DTO.
5. Prefer existing utility classes, enums, error codes, and conversion helpers.

## Review Questions

1. Did the change follow the existing module layering?
2. Did it introduce a dependency or framework pattern not already used?
3. Did it expose Entity directly to external APIs?
4. Did it preserve project-specific data isolation and auth context?

