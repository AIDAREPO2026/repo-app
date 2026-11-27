# Phase 0: Mobilise

**Dates:** 23 to 25 November 2026 · **Tasks:** 12 · **Points:** 26 (Dev 20, QA 6)

**Goal:** an empty application deploys to staging through CI, and the decisions it is built on are confirmed.

**Exit criteria**

- [ ] `docker compose up` starts every container locally, and `/healthz` returns 200
- [ ] A merge to `main` deploys to staging automatically through CI
- [ ] ITPED has confirmed or changed decisions D-01 to D-13
- [ ] The data model and the test plan are reviewed and merged

---

### P0-GOV-01 — Record ITPED confirmation of decisions

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 1 | Dev (tech lead) | None | [decisions.md](../decisions.md), Q-01 |

**Goal:** every decision in `decisions.md` has a recorded ITPED answer before the work that depends on it starts.

**Scope**

- Send `docs/decisions.md` to the ITPED Technical Lead with a request to confirm or change each decision.
- Record each answer in the Status column as `Confirmed by <name>, <date>` or `Changed: <summary>`.
- For each changed decision, update every task spec listed in its Affects column, and tell the developers who own those tasks.

**Security**

- D-02 and D-03 decide what visitors can see. If either changes, `P3-PUB-02` and `P4-SEC-02` must be re-checked.

**Acceptance criteria**

- [ ] Every decision D-01 to D-13 has a Status other than "Awaiting confirmation"
- [ ] Every changed decision is reflected in the affected task specs in the same pull request
- [ ] Q-01 is closed in the planning tracker

**Tests:** none. This is a documentation task.

---

### P0-GOV-02 — Confirm taxonomy baseline and Newly Added limit

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 1 | Dev (tech lead) | None | SRS Appendix A, FR-3.1, FR-6.1, Q-04, Q-05 |

**Goal:** the taxonomy seed and the Newly Added setting are agreed before `P2-CON-01` seeds them.

**Scope**

- Obtain ITPED's final taxonomy, or written acceptance of the Appendix A baseline in `decisions.md`.
- Confirm the six functional groups.
- Confirm the Newly Added count. FR-6.1 says 2 items from the last 15 days.
- Request the list of 70 Discoms with official email domains (Q-09), needed by `P1-ACC-01`.

**Security**

- None specific.

**Acceptance criteria**

- [ ] The taxonomy table in `decisions.md` matches what ITPED confirmed
- [ ] The `newly_added_count` default in `architecture.md` matches ITPED's answer
- [ ] Q-04 and Q-05 are closed, and Q-09 has a due date from ITPED

**Tests:** none.

---

### P0-OPS-01 — Provision India staging environment and object storage

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | Q-03 answered | SRS 2.4, 5.2, 5.3, [security.md](../security.md) |

**Goal:** a secure staging environment in India that CI can deploy to.

**Scope**

- Provision a Linux virtual machine in India with the provider ITPED selects. A MeitY-empanelled cloud or a Tier III data centre is preferred (SRS 2.4).
- Attach a separate encrypted data disk for SeaweedFS (D-14), sized to the agreed limit such as 100 GB. The `seaweedfs` container from `P0-OPS-02` stores its data there, in a private bucket with the prefixes `incoming/`, `files/`, `previews/` and `quarantine/`.
- Enable disk encryption on the virtual machine.
- Create a staging subdomain under ITPED-controlled DNS, and issue a TLS certificate with automatic renewal.
- Create an SMTP account for outbound email (registration, MFA codes, notifications).
- Create a deploy user with SSH key access only.
- Configure the firewall: 443 and 80 open, SSH only from named addresses, everything else closed.
- Write `docs/operations/environments.md` with the provider, region, sizes, DNS names and how to get access. Leave secrets out.

**Security**

- The bucket must not allow public reads or listing. Check with an anonymous request.
- Store all credentials in the team password manager, never in the repository or chat.
- Root login and password SSH login are disabled.

**Acceptance criteria**

- [ ] The staging URL serves a placeholder page over HTTPS with a valid certificate
- [ ] An anonymous request to the bucket is refused
- [ ] The virtual machine and its disks are in an Indian region, recorded in `environments.md`
- [ ] Encryption is confirmed on for the system disk and the storage data disk
- [ ] A test email sent through the SMTP account arrives

**Tests:** a manual checklist recorded in the pull request.

---

### P0-OPS-02 — Build the Docker Compose stack

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P0-SET-01` | [architecture.md](../architecture.md) runtime containers, SRS 5.6 |

**Goal:** one command starts the whole system on any machine, the same way on staging and production.

**Scope**

- `deploy/docker-compose.yml` with the containers `nginx`, `app`, `worker`, `beat`, `tusd`, `clamav`, `postgres`, `redis` and `seaweedfs` (D-14). The `postgres` service uses the official image pinned to a PostgreSQL 19 minor tag, such as `postgres:19.0-trixie`.
- `deploy/docker-compose.dev.yml` for local development, adding the Mailpit mail catcher.
- `Dockerfile` for `app`, and `Dockerfile.worker` adding LibreOffice, FFmpeg and libmagic.
- `deploy/nginx/default.conf` with:
    - HTTP to HTTPS redirect and the headers in [security.md](../security.md)
    - `client_max_body_size` for normal requests, separate from tusd
    - a proxy to `app`, a proxy for `/files/` to `tusd`, and an `internal` location for protected files
    - a basic `limit_req` zone for login and search
- `.env.example` listing every environment variable with a comment, and no real values.
- A `/healthz` route that checks the database and Redis connections.
- Health checks for every container.

**Security**

- Containers run as non-root users.
- Only `nginx` publishes ports to the host.
- The tusd hook endpoints and the internal location are not reachable from outside Nginx.

**Acceptance criteria**

- [ ] `docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.dev.yml up` starts all containers, and all show healthy
- [ ] `https://localhost/healthz` returns 200
- [ ] Every security header in `security.md` is present on a response
- [ ] Requests to the tusd hook paths and the internal location from outside return 404
- [ ] `.env.example` covers every variable the code reads

**Tests:** `test_p0_ops_02_healthz_checks_dependencies`, plus a header check script used later by CI.

---

### P0-OPS-03 — Set up CI

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P0-SET-01`, `P0-OPS-01`, `P0-OPS-02` | [conventions.md](../conventions.md), [security.md](../security.md), SRS 5.6 |

**Goal:** every pull request is checked automatically, and every merge deploys to staging.

**Scope**

- On every pull request:
    - `ruff check`, with rules `E`, `F`, `I`, `B`, `S`, `D` and `C901` (max complexity 10)
    - `ruff format --check`
    - `mypy app`
    - `pytest`, with PostgreSQL and Redis service containers on the same images as `deploy/docker-compose.yml`
    - `pip-audit`
    - a secret scan of the diff, using a tool the tech lead approves
    - `uv run python scripts/build_task_index.py --check`
    - a journal check: for the task code in the branch name and at the start of each commit subject, the pull request must change `docs/journal/<CODE>.md`
- On merge to `main`:
    - build and push images tagged with the commit hash
    - deploy to staging over SSH: pull images, run `alembic upgrade head`, restart containers
    - run a smoke check of `/healthz` and the security headers
- Branch protection on `main`: CI must pass, at least one approval, no direct pushes.
- A pull request template with the sections and self-review from `conventions.md`.

**Security**

- CI secrets are stored in the CI provider's secret store, scoped to the deploy job only.
- Pull requests from forks never receive secrets.

**Acceptance criteria**

- [ ] A pull request with a lint error, a failing test, a vulnerable dependency or a committed fake secret fails CI
- [ ] A pull request whose branch or commit-subject task code has no change to that task's journal file fails CI
- [ ] A merge to `main` deploys to staging, and the smoke check passes
- [ ] Direct pushes to `main` are refused
- [ ] The pull request template appears on new pull requests

**Tests:** prove each failure case once with a throwaway pull request, and record the links in this task's pull request.

---

### P0-SET-01 — Create repository, module structure and AGENTS.md

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev (tech lead) | None | [architecture.md](../architecture.md) folder layout, [conventions.md](../conventions.md) |

**Goal:** a repository whose structure and rules every developer and AI tool follows from the first commit.

**Scope**

- Create the folder layout from `architecture.md`, with empty `router.py`, `service.py`, `models.py` and `schemas.py` in each module, each with a module docstring stating its purpose.
- `pyproject.toml` with pinned dependencies from the approved list, plus Ruff, mypy and pytest settings.
- `AGENTS.md` at the root, copying the coding rules, shared-function table, testing rules and security-sensitive areas from `conventions.md` and `security.md`.
- `README.md` with how to run the project locally, run tests and create a migration.
- `.gitignore` covering `.env`, virtual environments, caches and build output.
- Add this `docs/` folder.

**Security**

- `.env` and other secret files are ignored from the first commit.

**Acceptance criteria**

- [ ] A new developer can clone, follow `README.md` and run the empty test suite
- [ ] `AGENTS.md` contains every rule in the coding rules section of `conventions.md`
- [ ] Every module has the four files with docstrings

**Tests:** `test_p0_set_01_app_imports` imports every module.

---

### P0-SET-02 — Add configuration, database connection and Alembic baseline

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P0-SET-01` | [architecture.md](../architecture.md) settings, SRS 5.6 |

**Goal:** the shared foundations every feature uses: configuration, database sessions, settings and time handling.

**Scope**

- `app/core/config.py`: a pydantic-settings class reading every environment variable, failing at startup if a required one is missing.
- `app/core/db.py`: SQLAlchemy engine, session factory and a `get_db` dependency that commits on success and rolls back on error.
- Alembic configured with naming conventions for constraints, and a first empty migration.
- `app/core/constants.py` with the fixed values from `architecture.md`, each commented with its FR.
- An `app_setting` table and `app/core/settings_store.py` with:
    - `get_setting(db, key)`, returning the stored value or the default
    - `set_setting(db, key, value, actor)`, validating type and bounds and writing an audit event (wired once `P1-AUD-01` lands)
- Validation rules for settings, including `limit_image_mb` never above 20 (D-01).
- `app/core/time.py` with `utc_now()` and `to_ist(dt)`.
- `app/main.py` creating the app, including routers, and setting structured JSON logging to stdout.

**Security**

- `set_setting` refuses values outside allowed bounds, so a setting cannot weaken a fixed rule.
- Logging setup removes `Authorization`, `Cookie` and `Set-Cookie` values from logs.

**Acceptance criteria**

- [ ] The app fails to start with a clear message when a required environment variable is missing
- [ ] `get_setting` returns defaults when nothing is stored
- [ ] `set_setting(limit_image_mb=21)` is refused
- [ ] `alembic upgrade head` and `alembic downgrade base` both run cleanly

**Tests:** `test_p0_set_02_setting_defaults`, `test_d01_image_limit_cannot_exceed_20`, `test_p0_set_02_missing_env_fails`.

---

### P0-ARC-01 — Design the database schema

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev (tech lead) | `P0-GOV-01`, `P0-SET-02` | SRS 6.1, Appendices A to C, [architecture.md](../architecture.md), [workflow.md](../workflow.md) |

**Goal:** one reviewed schema design that every feature task builds its migrations from.

**Scope**

- Write `docs/data-model.md` covering every table in the architecture data model overview: columns, types, null rules, defaults, keys, indexes and check constraints.
- Use these conventions:
    - UUID primary keys for anything that appears in a URL, and bigint identity for logs
    - text columns with check constraints for enumerations
    - `timestamptz` for every timestamp
    - no `ON DELETE CASCADE` on content, expert, Gallery or audit tables
- Include the partial unique index for one active Member login per organisation.
- Mark which columns are admin-only, matching Appendix A.
- Describe the version design: `content_item` holds identity, state and counters; `content_version` holds the editable fields; and `published_version_id` and `working_version_id` link them (D-09).
- List the database roles and their grants (see [security.md](../security.md)).

Each feature task creates its own tables in its own migration, following this design.

**Security**

- Admin-only columns are named and listed, so `P2-CON-02` can build view schemas without them.
- The application role has no UPDATE or DELETE on `audit_event`.

**Acceptance criteria**

- [ ] `docs/data-model.md` covers every entity in SRS 6.1 plus the tables in `architecture.md`
- [ ] A second developer has reviewed it
- [ ] Every admin-only field in Appendix A is marked

**Tests:** none. This is a design task.

---

### P0-ARC-02 — Write C4 documentation and decision records

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 1 | Dev | `P0-ARC-01` | [architecture.md](../architecture.md), SRS 5.6 |

**Goal:** a successor team can understand why the system is built this way.

**Scope**

- `docs/architecture/c4-context.md` and `c4-containers.md`, drawn in Mermaid.
- `docs/adr/` with a short template and these first records:
    - `0001` modular monolith
    - `0002` FastAPI with synchronous routes
    - `0003` server-side sessions instead of JWT
    - `0004` PostgreSQL full-text search instead of a search engine
    - `0005` protected file delivery through Nginx
    - `0006` self-hosted CAPTCHA (written in `P0-SEC-01`)

**Security**

- Decision records `0003` and `0005` state the security reasons for each choice.

**Acceptance criteria**

- [ ] Both C4 files render on the repository host
- [ ] Decision records 0001 to 0005 exist with context, decision and consequences

**Tests:** none.

---

### P0-SEC-01 — Confirm the self-hosted CAPTCHA approach

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 1 | Dev | None | FR-1.2, FR-13.7, SRS 5.3, 5.5 |

**Goal:** a CAPTCHA that blocks bots, keeps visitor data in India and does not block people using assistive technology.

**Scope**

- Evaluate ALTCHA (self-hosted proof of work), checking:
    - maintenance status
    - its Python server-side verification library
    - accessibility, with no visual puzzle
- Build a short spike that issues a challenge and verifies a solution.
- If ALTCHA is rejected, choose a self-hosted alternative with an audio option.
- Write decision record `0006`.

**Security**

- No visitor data may go to a third-party CAPTCHA service outside India.
- Challenges expire and cannot be replayed.

**Acceptance criteria**

- [ ] Decision record `0006` names the chosen approach, with its accessibility and data-location reasons
- [ ] The spike shows a solved challenge accepted, and a replayed one refused

**Tests:** a spike test kept for reuse in `P1-ACC-02`.

---

### P0-QA-01 — Write the test plan and test naming conventions

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | QA | None | SRS 8, [acceptance.md](../acceptance.md), [conventions.md](../conventions.md) |

**Goal:** everyone knows what is tested, where and when, and how test results prove the acceptance criteria.

**Scope**

- Write `docs/test-plan.md` covering:
    - test levels (unit, integration, end to end), tools and environments
    - entry and exit criteria for each phase
    - a mapping of every AC and GL code to its tests
    - test data rules: no real personal data
    - the defect process and severities from `conventions.md`
    - how the regression pack is run
- Include the security tests: refusal tests per role, direct-URL tests, the ZAP scan, and HTML scans for admin-only fields.

**Security**

- The plan includes a negative test for every row of the threats table in `security.md` that is in MVP scope.

**Acceptance criteria**

- [ ] Every AC code in `acceptance.md` maps to at least one planned test
- [ ] The tech lead has reviewed the plan

**Tests:** none.

---

### P0-QA-02 — Set up test data and Playwright

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | QA | `P0-OPS-02` | SRS 8, [decisions.md](../decisions.md) file limits |

**Goal:** reusable test data and an end-to-end test harness ready for Phase 1.

**Scope**

- Fixture data: three fictional Discoms with email domains, and one login per type, including a primary and an alternate Reviewer.
- Sample files in `tests/files/`:
    - one valid file per format
    - a JPG of 21 MB
    - the EICAR antivirus test file
    - a PDF renamed to `.docx`
- A script that generates a 1 GB MP4 on demand, rather than committing it.
- A Playwright project with a base URL from the environment, and sign-in helpers for each login type, including MFA.
- A nightly CI job running Playwright against staging.

**Security**

- Test passwords and MFA secrets come from CI secrets, never the repository.
- The EICAR file is the standard harmless test string, not real malware.

**Acceptance criteria**

- [ ] A sample Playwright test opens the staging home page in CI
- [ ] All sample files exist and are documented in `tests/files/README.md`

**Tests:** `tests/e2e/test_smoke.py`.
