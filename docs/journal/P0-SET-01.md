# P0-SET-01 — Create repository, module structure and AGENTS.md

| Field | Value |
| --- | --- |
| Status | Done |
| Owner | Raghvendra Singh |
| Branch | `chore/p0-set-01-project-structure` |
| Pull request | [AIDAREPO2026/repo-app#1](https://github.com/AIDAREPO2026/repo-app/pull/1) |
| Started | 2026-11-27 |
| Finished | 2026-11-27 |

Spec: [docs/tasks/phase-0-mobilise.md](../tasks/phase-0-mobilise.md)

## Log

Newest first. One line per working session: what was done, what is next.

| Date | Who | Entry |
| --- | --- | --- |
| 2026-11-27 | Raghvendra Singh | Pull request approved; set status to Done and squash-merged. There is no staging server or CI yet, so the staging check and CI items of the Definition of Done arrive with `P0-OPS-02` and `P0-OPS-03`. |
| 2026-11-27 | Raghvendra Singh | Moved the database target from PostgreSQL 16 to PostgreSQL 19, the latest release, in `docs/architecture.md` and `P0-OPS-02`. |
| 2026-11-27 | Raghvendra Singh | Pushed `main` and the task branch, opened [the pull request](https://github.com/AIDAREPO2026/repo-app/pull/1), set status to In review. Next: review and approval. |
| 2026-11-27 | Raghvendra Singh | Added the rule that any later change to a task updates its journal, and a CI journal check to `P0-OPS-03`. |
| 2026-11-27 | Raghvendra Singh | Added the task journal (this folder), the `P1-UI-02` design-system task and open question Q-11, and updated the shared tracker to match. Waiting for `main` on GitHub to open the pull request. |
| 2026-11-27 | Raghvendra Singh | Switched to uv with `uv.lock`, added the shared `apple-design` skill, the UI and motion rules, and the task index generator. |
| 2026-11-27 | Raghvendra Singh | Created the repository, module skeleton, `AGENTS.md`, README and docs. Ruff, mypy, pytest and pip-audit pass. |

## Decisions and deviations

| Date | Decision or deviation | Reason | Agreed by |
| --- | --- | --- | --- |
| 2026-11-27 | uv manages Python, the virtual environment and dependencies, with every package locked in `uv.lock` | Identical installs on laptops, CI and servers, and much faster installs than pip or Poetry | Raghvendra Singh |
| 2026-11-27 | No packaging config: the app is deployed from source, and pytest imports `app` from the repository root | The app is never published as a package | Raghvendra Singh |
| 2026-11-27 | `app/core/` files and `workers/celery_app.py` are not created yet | Their tasks (`P0-SET-02`, `P2-UPL-03`) add them, so no placeholder code sits unused | Raghvendra Singh |
| 2026-11-27 | Server-rendered pages with Jinja2 and HTMX, no separate frontend app; mobile apps later get JSON routes over the same services | Indexable public pages, simpler security, one stack for the MVP | Raghvendra Singh |
| 2026-11-27 | Added the shared `apple-design` skill and the UI and motion rules, plus the `P1-UI-02` design-system task | Consistent look and motion across five developers and AI tools | Raghvendra Singh |
| 2026-11-27 | Added `scripts/build_task_index.py` and this journal; the journal is the single home for task status | Status is updated in the same pull request as the code, so it cannot drift from the work | Raghvendra Singh |
| 2026-11-27 | PostgreSQL 19 (released 2026-11-19, supported to 2031-11-19) through the official Docker image, pinned to a minor tag in Compose | We run it in Docker, so the newest major costs nothing to adopt and gives the longest support window before an upgrade | Raghvendra Singh |

## Blockers

None. The missing `main` branch on GitHub was resolved on 2026-11-27.
