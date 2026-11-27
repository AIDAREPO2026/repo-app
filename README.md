# AIDA Digital Resource Repository

A governed knowledge repository for DISCOMs: Discoms submit content, ITPED reviews and approves it, and members and the public find and download what they are entitled to.

- **Stack:** FastAPI, Jinja2 and HTMX, PostgreSQL, Celery and Redis, Nginx, Docker Compose. See [docs/architecture.md](docs/architecture.md).
- **Rules for writing code:** [AGENTS.md](AGENTS.md)
- **All project docs and task specs:** [docs/README.md](docs/README.md)

## Project layout

```
app/                    the one FastAPI application (a modular monolith)
  main.py               creates the app and includes every module's router
  core/                 shared foundations: config, db, settings, email, storage...
  accounts/             Discoms, logins, passwords, sessions, MFA, route guards
  audit/                append-only audit log
  content/              taxonomy, items, versions, files, uploads, visibility
  workflow/             state machine, queues, notifications
  search/               browsing and search
  experts/              List of Experts (Go-To Discom Partner)
  gallery/              Technology Demonstration Gallery
  kpi/                  activity logging and KPIs
  public/               visitor-facing pages
  templates/            Jinja2 templates, one folder per module
  static/               CSS, JS, images; third-party libraries in vendor/
workers/                Celery background jobs
migrations/             Alembic database migrations
tests/                  mirrors app/, plus e2e/ and load/
deploy/                 Docker Compose, Dockerfiles, Nginx, release scripts
scripts/                developer scripts, such as the task index generator
docs/                   architecture, decisions, security and every task spec
.claude/skills/         shared Claude Code skills, loaded by every developer
```

Every feature module has the same four files:

| File | Holds | Never holds |
| --- | --- | --- |
| `router.py` | HTTP routes: parse input, call one service function, render | Business rules or queries |
| `service.py` | Business rules, taking `db` and `actor` explicitly | HTTP or template code |
| `models.py` | SQLAlchemy tables | Business rules or event listeners |
| `schemas.py` | Pydantic input and view schemas | Admin-only fields in Member or public views |

## Run locally

The project uses [uv](https://docs.astral.sh/uv/) for Python, dependencies and the virtual environment. Install it once:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then, from the repository root:

```bash
uv sync
```

```bash
cp .env.example .env
```

The pages need their CSS, built with Tailwind. Install [Node.js](https://nodejs.org/) 24 once, then:

```bash
npm ci
```

```bash
npm run watch:css
```

`watch:css` rebuilds `app/static/css/app.css` whenever a template changes. Use `npm run build:css` for a single build.


```bash
uv run uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/healthz. Running the app outside Docker, point `DATABASE_URL` and `REDIS_URL` in `.env` at `localhost` instead of the Compose service names.

`uv sync` installs the Python version in `.python-version` (3.12) if needed, creates `.venv/` and installs exactly what `uv.lock` lists. The app refuses to start until every variable in `.env.example` is set. To run the whole system in Docker instead, see [deploy/README.md](deploy/README.md).

Tests use their own PostgreSQL database, `aida_test` on port 5434, because they drop and recreate its tables, and their own Redis on port 6390:

```bash
docker run -d --name aida-postgres -e POSTGRES_USER=aida -e POSTGRES_PASSWORD=aida -e POSTGRES_DB=aida_test -p 5434:5432 postgres:19.0-trixie
```

```bash
docker run -d --name aida-redis-test -p 6390:6379 redis:8.8.4-trixie
```

Set `TEST_DATABASE_URL` or `TEST_REDIS_URL` to use different ones.

End-to-end tests drive a real browser with Playwright. Download its browser once, after `uv sync` and `npm ci` (the accessibility check uses the `axe-core` npm package):

```bash
uv run playwright install chromium
```

Then point them at a running portal, for example the local Docker stack:

```bash
E2E_BASE_URL=https://localhost:8443 uv run pytest tests/e2e
```

Large and antivirus test files are built on demand (see [tests/files/README.md](tests/files/README.md)):

```bash
uv run python scripts/make_test_files.py
```

## Dependencies

- Add a library with `uv add <name>==<version>`, or a dev tool with `uv add --dev <name>==<version>`. Only approved libraries (see [docs/architecture.md](docs/architecture.md)).
- Commit `pyproject.toml` and `uv.lock` together. Never edit `uv.lock` by hand.
- Servers install without dev tools: `uv sync --frozen --no-dev`.
- The CSS build tools are npm packages: add one with `npm install --save-exact --save-dev <name>@<version>`, then commit `package.json` and `package-lock.json` together.

## Checks

Run these before every pull request. CI runs the same ones (`P0-OPS-03`). Build the CSS first (`npm run build:css`), because a test checks the stylesheet is served.

```bash
uv run ruff check .
```

```bash
uv run mypy
```

```bash
uv run pytest
```

```bash
uv run pip-audit
```

## Create a migration

Number each migration with the next `--rev-id` (see [migrations/README.md](migrations/README.md)):

```bash
uv run alembic revision --autogenerate --rev-id 0003 -m "short description"
```

## Contributing

One task, one branch, one pull request, following [docs/conventions.md](docs/conventions.md). Never commit `.env` or other secrets.
