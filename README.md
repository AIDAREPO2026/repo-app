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

```bash
uv run uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/healthz.

`uv sync` installs the Python version in `.python-version` (3.12) if needed, creates `.venv/` and installs exactly what `uv.lock` lists. PostgreSQL, Redis and the full Docker stack arrive in `P0-SET-02` and `P0-OPS-02`.

## Dependencies

- Add a library with `uv add <name>==<version>`, or a dev tool with `uv add --dev <name>==<version>`. Only approved libraries (see [docs/architecture.md](docs/architecture.md)).
- Commit `pyproject.toml` and `uv.lock` together. Never edit `uv.lock` by hand.
- Servers install without dev tools: `uv sync --frozen --no-dev`.

## Checks

Run these before every pull request. CI runs the same ones (`P0-OPS-03`).

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

Alembic is set up in `P0-SET-02`. After that:

```bash
uv run alembic revision --autogenerate -m "short description"
```

## Contributing

One task, one branch, one pull request, following [docs/conventions.md](docs/conventions.md). Never commit `.env` or other secrets.
