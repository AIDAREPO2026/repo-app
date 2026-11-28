# P0-OPS-02 — Build the Docker Compose stack

| Field | Value |
| --- | --- |
| Status | Done |
| Owner | Raghvendra Singh |
| Branch | `feat/p0-ops-02-docker-compose` |
| Pull request | [AIDAREPO2026/repo-app#4](https://github.com/AIDAREPO2026/repo-app/pull/4) |
| Started | 2026-11-27 |
| Finished | 2026-11-27 |

Spec: [docs/tasks/phase-0-mobilise.md](../tasks/phase-0-mobilise.md)

## Log

Newest first. One line per working session: what was done, what is next.

| Date | Who | Entry |
| --- | --- | --- |
| 2026-11-28 | Raghvendra Singh | Fix: local testing over HTTPS failed (the browser refused the self-signed certificate, and port 8080's redirect dropped the 8443 port). Moved the HTTPS server's routes into `nginx/snippets/portal-routes.conf` and added `nginx/local-http.conf`, a plain HTTP server on 8081 that includes the same routes. Only `docker-compose.dev.yml` mounts it, published on 127.0.0.1. Checked: 200 on http://localhost:8081 and https://localhost:8443, the CSP and other headers on HTTP, `/internal/` still 404, and sign-in's CSRF cookie accepted over HTTP. |
| 2026-11-27 | Raghvendra Singh | Pull request approved; set status to Done and squash-merged. CI and the staging check arrive with `P0-OPS-03` and `P0-OPS-01`. |
| 2026-11-27 | Raghvendra Singh | At the tech lead's request, replaced the fixed `storage_limit_gb` with a free-space reserve read from SeaweedFS, and added task `P2-UPL-04`: an Admin Storage page, a 15-minute check, and portal and email alerts at 75% and 85% full. Phase 2 is now 23 tasks and 53 points; the MVP uses 83% of capacity. |
| 2026-11-27 | Raghvendra Singh | Moved the database and SeaweedFS data to host folders under `DATA_DIR`, and put SeaweedFS on its own `storage` network, at the tech lead's request. Proved a row and a stored file survive `docker compose down -v`, and that postgres, redis, clamav and beat cannot reach SeaweedFS. |
| 2026-11-27 | Raghvendra Singh | Published the SeaweedFS file browser on `127.0.0.1:8888` in development, at the tech lead's request; checked it lists the `aida` bucket and that the S3 port stays closed to the host. |
| 2026-11-27 | Raghvendra Singh | Opened [the pull request](https://github.com/AIDAREPO2026/repo-app/pull/4) and set status to In review. Next: review and approval. |
| 2026-11-27 | Raghvendra Singh | Built the Dockerfile, Compose stack, Nginx config and header check script, and made `/healthz` check the database and Redis. From empty volumes, every container reports healthy, `https://localhost/healthz` returns 200, all security headers are present, and the internal paths return 404 (checked on ports 8080 and 8443 because this machine already uses 80 and 443). Next: review. |
| 2026-11-27 | Raghvendra Singh | Changed D-14 from plain server disk to self-hosted SeaweedFS after review with the tech lead. |
| 2026-11-27 | Raghvendra Singh | Started the task. |

## Decisions and deviations

Anything decided while building that the spec does not say, and any change from the spec, with the reason. Write "None" if there are none.

| Date | Decision or deviation | Reason | Agreed by |
| --- | --- | --- | --- |
| 2026-11-27 | Upload space is limited by a reserve of real free space (`storage_reserve_percent`, default 10%, never under 5 GB), not a fixed size | A bigger disk is used as soon as it is mounted, and the database, which shares the disk, is protected too | Raghvendra Singh |
| 2026-11-27 | New task `P2-UPL-04` for the Storage page and alerts (2 points, Phase 2); warning and critical thresholds are constants (75%, 85%) | Admins must know before uploads stop. Phase 2 had 10 spare points, so no date moves | Raghvendra Singh |
| 2026-11-27 | The database and SeaweedFS data live in host folders under `DATA_DIR` (default `data/`, `/srv/aida` on servers), not Docker volumes | `docker compose down -v` deletes named volumes, which would wipe every file and the database. Host folders are never removed by Compose | Raghvendra Singh |
| 2026-11-27 | SeaweedFS is on a separate `storage` network joined only by `app`, `worker`, `tusd` and `nginx` | Its file browser and internal ports have no login inside Docker, so other containers must not reach it | Raghvendra Singh |
| 2026-11-27 | SeaweedFS's own JWT signing for its internal ports is not set up yet | The storage network already limits who can reach it; signing can be added in `P4-SEC-01` hardening if review wants a second layer | Raghvendra Singh |
| 2026-11-27 | In the development file only, Mailpit's inbox is published on `127.0.0.1:8025` and the SeaweedFS file browser on `127.0.0.1:8888` | Developers need to read captured mail and see stored files. Neither has a login, so both are bound to the local machine and never published on staging or production | Raghvendra Singh |
| 2026-11-27 | Root is used only by the one-shot `seaweedfs-init` (it hands a new disk to the SeaweedFS user) and by ClamAV's supervisor process; `clamd` and `freshclam` run as uid 1000, and the official PostgreSQL and Redis images switch to their own users | Every service process is non-root; these are the images' own start-up steps | Raghvendra Singh |
| 2026-11-27 | `celery` is installed with its `redis` extra, which adds `packaging` to the lock | Celery's Redis transport fails to import without it; no new library is added by hand | Raghvendra Singh |
| 2026-11-27 | One `deploy/Dockerfile` with `app` and `worker` targets, instead of a separate `Dockerfile.worker` | Both share the same Python layer; two files would repeat it | Raghvendra Singh |
| 2026-11-27 | A minimal `workers/celery_app.py` now, not in `P2-UPL-03` | The `worker` and `beat` containers need an app to run and report healthy | Raghvendra Singh |
| 2026-11-27 | `/healthz` returns `{"status": "ok"}` or 503 `{"status": "fail"}`, with the reason only in the logs | `P6-OPS-02` forbids dependency detail in the response | Raghvendra Singh |
| 2026-11-27 | Containers read the root `.env` through `env_file`, so `postgres`, `seaweedfs` and `tusd` also see secrets they do not use | Compose only reads `.env` from `deploy/` for interpolation; one file is simpler, and every container runs on the same server under the same operator. Split per-service files if a reviewer asks | Raghvendra Singh |
| 2026-11-27 | Published ports default to 80 and 443 and can be changed with `HTTP_PORT` and `HTTPS_PORT` | Developers may already run a web server on 80 and 443 | Raghvendra Singh |
| 2026-11-27 | tusd's hooks already point at `/internal/tusd-hooks`, which does not exist yet | Every upload is refused at pre-create until `P2-UPL-01`, which is the safe default | Raghvendra Singh |
| 2026-11-27 | Files are stored in self-hosted SeaweedFS (open-source edition, Apache-2.0) on our own server, with uploads refused when they would eat into a free-space reserve read from the real disk (D-14). It runs in the main stack, not only in development | No managed object storage is available yet. SeaweedFS is actively maintained, free at our size, and speaks S3, so a managed S3 can replace it by changing settings. The storage check is built in `P2-UPL-02`, where the upload hook is | Raghvendra Singh |
| 2026-11-27 | Mailpit is the local mail catcher | MIT licence, a single small container with a web inbox; MailHog is unmaintained | Raghvendra Singh |

## Blockers

What stops the task, who can unblock it, and since when. Write "None" if there are none.

None.
