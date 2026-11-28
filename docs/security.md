# Security

Security is a release gate, not a later phase. Every task spec has a **Security** section, and these rules apply to all code. The target is OWASP ASVS Level 2 and the OWASP Top 10 (SRS 5.3). Use the ASVS version agreed with the independent reviewer in `P6-SEC-01`.

## What we protect

| Class | Examples | Rule |
| --- | --- | --- |
| Public content | Public items, consented expert fields, Gallery listings | Integrity: only the Approver can publish |
| Restricted content | Restricted items and their files | Members and privileged logins only. Never reachable by URL guessing. Encrypted at rest |
| Internal content | Admin internal workspace (Phase 5) | Admin only. Encrypted at rest. Never in search, listings or counts |
| Personal data | Member contact emails, expert profiles, IP addresses | DPDP Act: notice, consent, purpose, retention and deletion |
| Admin-only metadata | Functional group, access tier value, jurisdiction, rights declaration, owner and review fields | Never rendered to Members or visitors (FR-3.3, D-03) |
| Credentials and secrets | Password hashes, session tokens, TOTP secrets, API keys, storage keys | Never logged or committed. Hashed or encrypted at rest |
| Audit trail | `audit_event` | Append-only, retained for 3 years |

## Main threats and controls

| Threat | Control | Task |
| --- | --- | --- |
| Password guessing and credential stuffing | 12-character policy, argon2id hashing, lockout after 5 failures, CAPTCHA on registration and reset, generic error messages | `P1-ACC-02`, `P1-ACC-04` |
| Shared Member login misuse | Session and device identifiers in every audit event, 5-session limit, Member device list | `P1-ACC-06`, `P1-ACC-07` |
| Privileged account takeover | Mandatory MFA, named individual accounts, no shared privileged credentials | `P1-ACC-09`, `P1-ACC-10` |
| Session hijacking or fixation | Random 256-bit tokens stored hashed, rotation at login and MFA, secure cookies, 30-minute idle timeout | `P1-ACC-06` |
| Cross-site request forgery | Per-session CSRF token checked on every state-changing request | `P1-ACC-06` |
| Privilege escalation | `require_login_type()` on every route, with refusal tests for every role | `P1-ACC-08` |
| Reaching a Restricted file by URL | One visibility module, file delivery only through `protected_file_response()`, storage never public | `P2-CON-06`, `P3-VIEW-03` |
| Teaser leakage | Teaser view schema has no file fields. Restricted items flagged No are absent everywhere | `P3-PUB-02`, `P4-SEC-02` |
| Admin-only field leakage | Separate view schemas per audience, plus tests that scan rendered HTML | `P2-CON-02`, `P2-QA-03` |
| Malicious uploads | Format and size checks before upload, file-type sniffing, ClamAV, quarantine | `P2-UPL-02`, `P2-UPL-03` |
| Malicious SCORM packages | Zip-bomb and path-traversal checks, every file scanned, served from a separate cookieless origin | `P5-CON-01`, `P5-VIEW-01` |
| Stored cross-site scripting | Jinja autoescaping always on, no `|safe` on user input, strict Content Security Policy | `P1-UI-01` |
| SQL injection | SQLAlchemy bound parameters only. No string-built SQL | All |
| Server-side request forgery from the link checker | Block private and loopback addresses, no redirects to internal addresses, timeouts | `P5-CON-02` |
| Harvesting expert emails | Reveal on click, rate limited, never in page source | `P3-EXP-02` |
| Download abuse by bots | 50 downloads per IP per hour, then a CAPTCHA | `P4-PUB-01` |
| Denial of service | Nginx rate limits, upload size checks before upload, worker timeouts | `P0-OPS-02`, `P2-UPL-02` |
| Tampering with the audit trail | Database trigger blocks update and delete, and the app's database role has no UPDATE or DELETE on the table | `P1-AUD-01` |
| Vulnerable dependencies | `pip-audit` in CI, every package locked in `uv.lock`, monthly update review | `P0-OPS-03` |
| Secret leakage | Secrets only in environment variables, secret scanning in CI, nothing sensitive in logs | `P0-OPS-03` |
| Insider misuse | Least privilege, full audit of administrative actions, named accounts | `P1-AUD-01`, `P1-ACC-09` |
| Data loss | Daily encrypted backups for 30 days, restore rehearsal, India-only storage | `P4-OPS-01`, `P6-OPS-01` |

## Mandatory controls

### Authentication and sessions

- Hash passwords with argon2id through argon2-cffi, using the library's recommended parameters.
- Enforce at least 12 characters with letters, numbers and symbols (FR-1.7).
- Lock an account for 15 minutes after 5 consecutive failures (FR-1.7). Log every failure.
- Show the same message for an unknown User ID, a wrong password and a locked account, so login never reveals which accounts exist.
- Make session tokens 32 random bytes from `secrets.token_urlsafe`, and store only their SHA-256 hash.
- Rotate the session token at login and after MFA.
- Set cookies with `HttpOnly`, `Secure`, `SameSite=Lax` and `Path=/`, with no `Domain` attribute.
- Require MFA for Admin, Reviewer and Approver (FR-2.8), with TOTP secrets encrypted using a key from the environment.
- Make password reset and set-password tokens single-use, store them hashed, and expire them after 60 minutes.
- Build emailed links from the configured `PORTAL_URL`, never from the request's `Host` header, which the sender controls.
- Keep link tokens out of logs: add any new address that carries one to `app/core/log_setup.py` and turn its Nginx access log off.

### Access control

- Every route declares its allowed login types with `require_login_type()`, or is marked `public_route`. A route with neither fails a CI test that lists all routes.
- Every query for items, files, experts or listings goes through the visibility functions. Never filter by hand in a route.
- Return 404, not 403, when an anonymous visitor or Member asks for something they cannot see, so the response never confirms it exists.
- Default to the most restrictive tier when classification is missing (SRS 5.3).

### Input, output and files

- Validate all input with Pydantic schemas, including length limits on every text field.
- Keep Jinja autoescaping on. Never use `|safe` or `Markup()` on user-supplied text.
- Check uploads by extension, sniffed type and size, then scan with ClamAV, before anyone else can open them.
- Use generated storage keys, never user file names, and send user file names only in `Content-Disposition`.
- Send `X-Content-Type-Options: nosniff` with every response.

### Security headers

Nginx sets these on every response:

| Header | Value |
| --- | --- |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self'; worker-src 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |

Restricted pages and files also send `Cache-Control: private, no-store`.

### Data protection

- Use TLS 1.2 or later only.
- Encrypt Restricted and internal files at rest with disk encryption on the storage data disk (D-14), and encrypt database and backup disks.
- Keep all data, including backups, in India (SRS 5.3).
- Store IP addresses in activity logs as a salted SHA-256 hash. Audit events keep the raw IP for incident reporting.
- Show a privacy notice wherever personal data is collected: registration, the expert entry form and notification email settings.

### Logging and monitoring

- Log authentication events, access denials, administrative actions, workflow transitions, scan results, rate-limit hits and setting changes.
- Never log passwords, tokens, one-time codes, TOTP secrets or file contents.
- Keep audit events for at least 3 years, with the latest 180 days searchable online (FR-12.1).
- Keep security logs in India for at least 180 days, to support CERT-In directions. Confirm the current directions with ITPED.
- Alert on repeated lockouts, quarantined files, scanner errors and failed backups.

### Secrets and infrastructure

- Store secrets in environment files on the servers with `600` permissions, separate for each environment, and in the team password manager. Never commit them.
- Rotate secrets when a team member with access leaves.
- Use separate database roles: a migration role that owns the schema, and an application role without DELETE on content tables or UPDATE and DELETE on `audit_event`.
- Expose only ports 443 and 80 to the internet. Port 80 only redirects. Restrict SSH to named keys and known addresses.
- Make internal Nginx locations and the tusd hook endpoints unreachable from outside.

## Secure development process

| Stage | Check | Task |
| --- | --- | --- |
| Every pull request | Ruff security rules (`S`), type check, tests, `pip-audit`, secret scan | `P0-OPS-03` |
| Security-sensitive pull requests | Two reviewers and the `security` label (see [conventions.md](conventions.md)) | All |
| End of Phases 1, 2 and 4 | Human line-by-line review of the sensitive areas | `P1-SEC-01`, `P2-SEC-01`, `P4-SEC-02` |
| Before the MVP | OWASP ZAP authenticated scan, high findings fixed | `P4-SEC-01` |
| Before Restricted content goes live | Independent review and penetration test, critical and high findings closed | `P6-SEC-01`, `P6-SEC-02` |
| Monthly after launch | Dependency and base-image update review | Maintenance |

## Release gates

| Gate | Condition |
| --- | --- |
| MVP (17 December 2026) | AC-01 to AC-22 pass. No open S1 or S2 security defect. Only Public or test content is loaded |
| Restricted content live | `P6-SEC-02` is Done and the reviewer confirms critical and high findings are closed |
| Production go-live | All GL criteria in [acceptance.md](acceptance.md) pass |

## Incident response

1. **Detect:** an alert, a user report or a log review finds a suspected incident.
2. **Contain:** the on-call developer ends affected sessions, disables affected accounts, or takes the site into maintenance mode.
3. **Report:** tell the ITPED Technical Lead at once. ITPED reports to CERT-In within the time its directions require (6 hours under the 2022 directions; confirm the current rule).
4. **Assess personal data:** if personal data is affected, ITPED handles notification under the DPDP Act and its rules.
5. **Recover:** fix the cause, restore from backup if needed, and rotate any exposed secrets.
6. **Learn:** write a short incident report in `docs/operations/incidents/` within 5 working days.

`P4-DOC-01` puts these steps into the operations runbook with names and contact details.
