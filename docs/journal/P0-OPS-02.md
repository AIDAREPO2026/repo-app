# P0-OPS-02 — Build the Docker Compose stack

| Field | Value |
| --- | --- |
| Status | In progress |
| Owner | Raghvendra Singh |
| Branch | `feat/p0-ops-02-docker-compose` |
| Pull request | Not opened |
| Started | 2026-11-27 |
| Finished | Not finished |

Spec: [docs/tasks/phase-0-mobilise.md](../tasks/phase-0-mobilise.md)

## Log

Newest first. One line per working session: what was done, what is next.

| Date | Who | Entry |
| --- | --- | --- |
| 2026-11-27 | Raghvendra Singh | Built the Dockerfile, Compose stack, Nginx config and header check script, and made `/healthz` check the database and Redis. From empty volumes, every container reports healthy, `https://localhost/healthz` returns 200, all security headers are present, and the internal paths return 404 (checked on ports 8080 and 8443 because this machine already uses 80 and 443). Next: review. |
| 2026-11-27 | Raghvendra Singh | Changed D-14 from plain server disk to self-hosted SeaweedFS after review with the tech lead. |
| 2026-11-27 | Raghvendra Singh | Started the task. |

## Decisions and deviations

Anything decided while building that the spec does not say, and any change from the spec, with the reason. Write "None" if there are none.

| Date | Decision or deviation | Reason | Agreed by |
| --- | --- | --- | --- |
| 2026-11-27 | Mailpit publishes its inbox on `127.0.0.1:8025`, in the development file only | Developers need to read captured mail; it is bound to the local machine and never runs on staging or production | Raghvendra Singh |
| 2026-11-27 | Root is used only by the one-shot `seaweedfs-init` (it hands a new disk to the SeaweedFS user) and by ClamAV's supervisor process; `clamd` and `freshclam` run as uid 1000, and the official PostgreSQL and Redis images switch to their own users | Every service process is non-root; these are the images' own start-up steps | Raghvendra Singh |
| 2026-11-27 | `celery` is installed with its `redis` extra, which adds `packaging` to the lock | Celery's Redis transport fails to import without it; no new library is added by hand | Raghvendra Singh |
| 2026-11-27 | One `deploy/Dockerfile` with `app` and `worker` targets, instead of a separate `Dockerfile.worker` | Both share the same Python layer; two files would repeat it | Raghvendra Singh |
| 2026-11-27 | A minimal `workers/celery_app.py` now, not in `P2-UPL-03` | The `worker` and `beat` containers need an app to run and report healthy | Raghvendra Singh |
| 2026-11-27 | `/healthz` returns `{"status": "ok"}` or 503 `{"status": "fail"}`, with the reason only in the logs | `P6-OPS-02` forbids dependency detail in the response | Raghvendra Singh |
| 2026-11-27 | Containers read the root `.env` through `env_file`, so `postgres`, `seaweedfs` and `tusd` also see secrets they do not use | Compose only reads `.env` from `deploy/` for interpolation; one file is simpler, and every container runs on the same server under the same operator. Split per-service files if a reviewer asks | Raghvendra Singh |
| 2026-11-27 | Published ports default to 80 and 443 and can be changed with `HTTP_PORT` and `HTTPS_PORT` | Developers may already run a web server on 80 and 443 | Raghvendra Singh |
| 2026-11-27 | tusd's hooks already point at `/internal/tusd-hooks`, which does not exist yet | Every upload is refused at pre-create until `P2-UPL-01`, which is the safe default | Raghvendra Singh |
| 2026-11-27 | Files are stored in self-hosted SeaweedFS (open-source edition, Apache-2.0) on our own server, with uploads refused once `storage_limit_gb` is reached (D-14). It runs in the main stack, not only in development | No managed object storage is available yet. SeaweedFS is actively maintained, free at our size, and speaks S3, so a managed S3 can replace it by changing settings. The storage check is built in `P2-UPL-02`, where the upload hook is | Raghvendra Singh |
| 2026-11-27 | Mailpit is the local mail catcher | MIT licence, a single small container with a web inbox; MailHog is unmaintained | Raghvendra Singh |

## Blockers

What stops the task, who can unblock it, and since when. Write "None" if there are none.

| Since | Blocker | Who can unblock it |
| --- | --- | --- |
