# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in InterviewCraft, please **do not** open a public GitHub issue with the details.

Instead:

1. Go to **[Security → Report a vulnerability](../../security/advisories/new)** on this repository (GitHub private advisory).
2. Include at minimum:
   - A clear description of the vulnerability
   - Steps to reproduce
   - Potential impact (what data or functionality is at risk)
   - Your GitHub handle (optional, for credit)

A maintainer will acknowledge your report within **48 hours** and work with you privately to validate and patch the issue before any public disclosure.

## Scope

The following are in scope:

- Authentication bypass or privilege escalation
- Exposure of user API keys (BYOK) or session tokens
- SQL injection, XSS, CSRF, or other OWASP Top 10 vulnerabilities
- Insecure storage or transmission of personal data
- Secrets or credentials leaked in logs, responses, or error messages

## Out of Scope

- Denial-of-service attacks
- Issues in third-party dependencies (report to their maintainers directly)
- Vulnerabilities requiring physical access to the server

## Disclosure Policy

We follow [coordinated disclosure](https://docs.github.com/en/code-security/security-advisories/about-coordinated-disclosure-of-security-vulnerabilities). We ask that you give us reasonable time to patch before any public disclosure. We will credit reporters in the release notes unless they prefer to remain anonymous.
