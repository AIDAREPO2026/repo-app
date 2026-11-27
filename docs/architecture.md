# Architecture

The system is a layered modular monolith: one FastAPI application, one PostgreSQL database and separate Celery workers. Nginx sits in front and serves protected files only after the application approves each request.

## Stack

| Layer | Technology | Responsibility |
| --- | --- | --- |
| Edge | Nginx | TLS, HSTS, rate limits, protected file and video delivery |
| Web pages | Jinja2, HTMX, Bootstrap 5 (all served locally, no CDN) | Server-rendered portal and indexable public pages |
| Application | FastAPI, Pydantic v2, Uvicorn, plain `def` routes | Routing and input validation |
| Business rules | `service.py` in each module | Workflow, permissions, consent and limits |
| Data | PostgreSQL 19 (official Docker image `postgres:19`), SQLAlchemy 2, Alembic, psycopg 3 | Records, full-text search and the append-only audit table |
| Files | S3-compatible object storage in India: self-hosted SeaweedFS (D-14), tusd, Uppy | Stored files and resumable uploads |
| Background work | Celery, Redis | Scanning, previews, notifications and scheduled jobs |
| Scanning and previews | ClamAV (clamd), LibreOffice headless, PDF.js, FFmpeg (`ffprobe`) | Malware checks, Office previews and media metadata |
| Sessions and MFA | Database session table, argon2-cffi, pyotp | 5-device limit, idle timeout and privileged MFA |
| Delivery | Docker Compose, CI pipeline | Same deployment on any cloud or in-house server |

## Approved libraries

**Runtime:** fastapi, uvicorn, pydantic, pydantic-settings, sqlalchemy, alembic, psycopg, jinja2, python-multipart, argon2-cffi, pyotp, qrcode, cryptography, celery, redis, boto3, python-magic, openpyxl, pypdf, httpx, and the ALTCHA server library (confirmed in `P0-SEC-01`).

**Front end, served locally:** Bootstrap 5, HTMX, Uppy, PDF.js.

**Development and test:** pytest, playwright, locust, ruff, mypy, pip-audit.

**Python tooling:** uv manages the Python version (`.python-version`), the virtual environment and dependencies. `uv.lock` pins every package, including indirect ones, so laptops, CI and servers install identical versions.

Add a library only with tech lead approval, and update this list in the same pull request.

## Folder layout

```
app/
  main.py               creates the FastAPI app and includes every router
  core/                 config, db, sessions, csrf, captcha, email, storage,
                        settings_store, constants, clamav, time helpers,
                        log_setup (JSON logs)
  accounts/             organisations, logins, passwords, lockout, MFA, guards
  audit/                append-only audit log and its search screen
  content/              modules, taxonomy, items, versions, files, uploads,
                        visibility, delivery, previews, bulk import
  workflow/             transition table, apply_action, queues, notifications
  search/               browsing, central and module search, search logging
  experts/              List of Experts (Go-To Discom Partner)
  gallery/              Technology Demonstration Gallery
  kpi/                  activity logging and, later, the dashboard
  public/               public home, item and teaser pages, legal pages
  templates/            Jinja2 templates, grouped by module
  static/               vendored CSS, JS and images
workers/
  celery_app.py         Celery app and beat schedule
migrations/             Alembic
tests/                  mirrors app/
docs/                   these documents
deploy/                 docker-compose files, nginx config, Dockerfiles
```

Each module contains `router.py`, `service.py`, `models.py` and `schemas.py` (see [conventions.md](conventions.md)).

## Runtime containers

| Container | Purpose |
| --- | --- |
| `nginx` | TLS, static files, rate limits, proxy to `app` and `tusd`, internal protected-file location |
| `app` | FastAPI with several Uvicorn workers |
| `worker` | Celery worker with ClamAV client, LibreOffice and FFmpeg installed |
| `beat` | Celery beat for scheduled jobs |
| `tusd` | Resumable upload server writing to object storage |
| `clamav` | clamd with daily signature updates (`freshclam`) |
| `postgres` | Database, official image pinned to a minor tag such as `postgres:19.0-trixie` so every environment runs the same build. Production can use a managed PostgreSQL 19 in India instead |
| `redis` | Celery broker and rate-limit counters |
| `mailpit` | Local development only: catches outgoing email |
| `seaweedfs` | S3-compatible object storage, open-source edition (Apache-2.0), on the server's encrypted data disk (D-14). Production can switch to a managed S3 in India by changing the endpoint and keys |

## Key flows

**Page request:** browser → Nginx → app. The session middleware loads the session from its cookie and checks the idle timeout. The route calls a service function, and the service checks permissions and visibility. The template then renders a view schema.

**Upload:**

1. Uppy sends the file to `/files/` (tusd) in 50 MB chunks.
2. tusd calls the app's pre-create hook. The app checks the session, the role, the format and the size limit, and refuses before any byte is stored.
3. When the upload finishes, tusd calls the post-finish hook. The app records a `content_file` with `scan_status = pending` and queues `scan_file`.
4. The worker checks the file type against the extension and scans it with ClamAV.
5. A clean file moves to the private `files/` prefix. An infected or mismatched file moves to `quarantine/`, and the submitter is notified.

**Protected download or stream:**

1. The browser requests `/items/{id}/files/{file_id}/view` or `/download`.
2. The app checks `can_open(viewer, item)` and logs the view or download.
3. The app returns an `X-Accel-Redirect` to an internal Nginx location with a short-lived presigned storage URL.
4. Nginx streams the bytes, with range support for video and audio seeking.

The storage URL is never sent to the browser.

**Workflow action:** the route calls `workflow.service.apply_action(db, subject, action, actor, comment)`. It checks the transition table and guard conditions, updates the state, and writes a `workflow_event` and an audit event in one transaction. It then creates notifications.

## File storage

Files are stored in one private bucket on SeaweedFS, an open-source S3-compatible server that runs as a container on our own server in India (D-14). The bucket has the prefixes `incoming/` (tusd uploads), `files/` (clean files), `previews/` and `quarantine/`. The app, tusd and Nginx talk to it only through the S3 API, so moving to a managed S3 in India later changes the endpoint and keys, not the code.

The database and SeaweedFS's data live in host folders under `DATA_DIR` on the encrypted data disk, not in Docker volumes, so removing containers never deletes them. SeaweedFS sits on its own `storage` network, reachable only from `app`, `worker`, `tusd` and `nginx`.

The data disk has a fixed size, such as 100 GB, shared by the files and the database. Before an upload starts, the tusd pre-create hook reads the disk's real free space from SeaweedFS and refuses the upload if it would leave less than the reserve: `storage_reserve_percent` of the disk (default 10%), and never less than 5 GB (`P2-UPL-02`). No byte is stored for a refused upload. A bigger disk is used as soon as it is mounted, with no setting to change.

Admins see used and free space, a 30-day trend and an estimate of days until full on the Storage page. A scheduled check every 15 minutes alerts every Admin, in the portal and by email, when the disk passes 75% (warning) and 85% (critical) full (`P2-UPL-04`). The operations monitoring in `P6-OPS-02` alerts the on-call team as well.

## Data model overview

`P0-ARC-01` produces the full schema in `docs/data-model.md`. The main tables are:

| Table | Key fields | Created in |
| --- | --- | --- |
| `app_setting` | key, value, updated_by, updated_at | `P0-SET-02` |
| `organisation` | name, email_domain, status | `P1-ACC-01` |
| `login` | user_id, email, password_hash, login_type, organisation_id, is_alternate, status, mfa fields, lockout fields | `P1-ACC-08` |
| `user_session` | token_hash, login_id, csrf_token, mfa_pending, created_at, last_seen_at, ended_at, end_reason, ip, user_agent | `P1-ACC-06` |
| `login_attempt` | attempted_user_id, login_id, ip, user_agent, success, reason, at | `P1-ACC-04` |
| `audit_event` | occurred_at, actor_login_id, actor_kind, session_id, ip, action, target_type, target_id, result, details | `P1-AUD-01` |
| `module`, `subcategory`, `functional_group` | name, slug, status, display_order | `P2-CON-01` |
| `content_item` | item_type, state, published_version_id, working_version_id, counters, endorsement, assignment, timestamps | `P2-CON-02` |
| `content_version` | title, module, subcategory, functional_group, access_tier, jurisdiction, source fields, year, summary, external_url, rights declaration, public_teaser, search vector | `P2-CON-02` |
| `content_file` | version_id, storage_key, original_filename, mime_type, size_bytes, sha256, scan_status, preview_storage_key, media metadata | `P2-CON-02` |
| `workflow_event` | subject_type, subject_id, from_state, to_state, action, actor_login_id, comment, at | `P2-WF-01` |
| `storage_check` | checked_at, total_bytes, used_bytes, level | `P2-UPL-04` |
| `notification` | recipient_login_id, event_type, subject reference, channel, status, created_at, read_at | `P2-WF-05` |
| `view_event`, `download_event`, `search_log` | subject, actor_kind, login_id, session_id, ip_hash, query, results, at | `P3-LIST-02`, `P3-SRCH-01` |
| `expert_profile` | Appendix B fields, consent per field, state | `P3-EXP-01` |
| `tech_listing` | Appendix C fields, fee terms, declarations, state | `P3-GAL-01` |

## Settings

These values are configurable by Admin through `app_setting` and read with `get_setting()`. Values the SRS fixes are constants in `app/core/constants.py`.

| Key | Default | Admin-editable | Source |
| --- | --- | --- | --- |
| `limit_document_mb` | 25 | Yes | FR-3.5 |
| `limit_image_mb` | 20 | Yes, but never above 20 | FR-3.5, D-01 |
| `limit_media_mb` | 1024 | Yes | FR-3.5 |
| `sixth_session_policy` | `block` | Yes (`block` or `end_oldest`) | FR-2.3, D-10 |
| `anon_downloads_per_hour` | 50 | Yes | FR-13.7 |
| `newly_added_count` | 2 | Yes | FR-6.1, Q-05 |
| `newly_added_days` | 15 | Yes | FR-6.1 |
| `storage_reserve_percent` | 10 | Yes (5 to 50; never under 5 GB) | D-14 |
| `digest_frequency` | `daily` | Yes (`daily` or `weekly`, Phase 5) | FR-6.5 |

| Constant | Value | Source |
| --- | --- | --- |
| `PASSWORD_MIN_LENGTH` | 12 | FR-1.7 |
| `LOCKOUT_ATTEMPTS` | 5 | FR-1.7 |
| `LOCKOUT_MINUTES` | 15 | FR-1.7 |
| `IDLE_TIMEOUT_MINUTES` | 30 | FR-1.7 |
| `MEMBER_MAX_SESSIONS` | 5 | FR-2.3 |
| `RESUMABLE_CHUNK_MB` | 50 | FR-3.12 |
| `AUDIT_ONLINE_DAYS` | 180 | FR-12.1 |
| `EXPERT_DELETION_WORKING_DAYS` | 2 | FR-8.3 |
| `IMAGE_LIMIT_MAX_MB` | 20 | D-01 |
| `STORAGE_RESERVE_MIN_GB` | 5 | D-14 |
| `STORAGE_WARNING_PERCENT` | 75 | D-14 |
| `STORAGE_CRITICAL_PERCENT` | 85 | D-14 |

## Environments

| Environment | Purpose | Data |
| --- | --- | --- |
| Development | Each developer's machine, using Docker Compose | Fake data only |
| Staging | Integration, QA and demos | Test data, and Public content for loading checks |
| Production | MVP from 17 December, then go-live | Public or test content until the security review is complete (SRS 5.3) |

Staging and production are hosted in India, with backups also in India (SRS 2.4, 5.3).

## Security baseline

- HTTPS only, with HSTS. HTTP redirects to HTTPS.
- Cookies are `HttpOnly`, `Secure` and `SameSite=Lax`.
- Content Security Policy uses self-hosted scripts only, with no inline scripts.
- Restricted and internal files are encrypted at rest, using disk encryption on the storage data disk (D-14).
- Restricted responses carry `Cache-Control: private, no-store`.
- Logs never contain passwords, tokens, one-time codes or full file contents.
- IP addresses in activity logs are stored as a salted hash. Audit events keep the raw IP to support CERT-In reporting.

## Standards

Twelve-Factor App, OpenAPI 3 for future mobile routes under `/api/v1`, role-based access control with item-level checks, OWASP Top 10 and ASVS Level 2, WCAG 2.1 Level AA, the DPDP Act 2023, and the C4 model with decision records in `docs/adr/`.
