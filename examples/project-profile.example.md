# ai-coding-java Project Profile

Project type: legacy
Technology stack: Java 8 + Spring Boot 2.x + Maven + MyBatis + MySQL + Redis
Verification level: standard
Template policy: local-auxiliary
Data boundary: school + school_year

## Required Confirmation

- Build command: mvn -DskipTests compile
- Test command: mvn test
- Start command: project-specific
- Database: project-specific dev/test DB only
- Cache: Redis when configured
- External systems: project-specific
- API verification method: local start + curl with dev/test data when feasible
- Delivery report path: .ai-coding-java/reports/delivery-report.md
- P1 waiver owner and record path: project owner / delivery report
- RD artifact policy: local-only
- Hook mode: warn

## Notes

- Project `AGENTS.md` and business rules override generic ai-coding-java suggestions.
- Keep this profile free of secrets and long logs.
