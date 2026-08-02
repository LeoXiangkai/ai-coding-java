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
- New project macro modules: not applicable for this legacy example
- New project core flows: not applicable for this legacy example
- Module micro design entry: .ai-coding-java/artifacts/<work-id>/design-brief.md
- Legacy module entry points: project-specific Controller / route / menu
- Legacy reuse points: project-specific Service / Mapper / existing page
- Legacy forbidden change scope: project-specific
- Secondary development impact check: project-map + design brief + focused verification
- API verification method: local start + curl with dev/test data when feasible
- Delivery report path: .ai-coding-java/reports/delivery-report.md
- P1 waiver owner and record path: project owner / delivery report
- RD artifact policy: local-only
- Hook mode: warn

## Notes

- Project `AGENTS.md` and business rules override generic ai-coding-java suggestions.
- Keep this profile free of secrets and long logs.
