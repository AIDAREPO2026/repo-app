# Migrations

Alembic migrations, numbered `0001`, `0002` and so on. `migrations/env.py` reads the database URL from the app config, and the shared naming convention in `app/core/db.py` names every constraint.

- Create one: `uv run alembic revision --autogenerate --rev-id 0003 -m "short description"`, then read and tidy the generated file.
- Apply: `uv run alembic upgrade head`. Undo all: `uv run alembic downgrade base`.
- Every migration needs a downgrade path, or a written reason in the pull request why it cannot have one.
- A new models module must be imported in `migrations/env.py` so autogenerate sees its tables.
