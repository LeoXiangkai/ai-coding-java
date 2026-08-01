# Security And Logging Rule

Use for authentication, authorization, sensitive fields, logs, config, credentials, external calls, and review.

## P0

1. No plaintext passwords, tokens, keys, production credentials, or private certificates in code, docs, logs, or scripts.
2. No sensitive personal data in logs unless masked according to project policy.
3. No auth or data-scope bypass.
4. No unsafe external input entering SQL, file paths, shell commands, URLs, or deserialization.

## P1

1. Use project-approved config, encryption, secret, and credential mechanisms.
2. Log business context needed for diagnosis, but avoid oversized payloads.
3. Use INFO for key business actions, WARN for recoverable risks, ERROR for system failures.
4. External calls need timeout, error mapping, and safe message exposure.

## Review Questions

1. Can any log line expose credential or identity-sensitive data?
2. Can a caller access another tenant, organization, school, year, or region?
3. Does an external error leak implementation details to users?
4. Are config defaults safe per environment?

