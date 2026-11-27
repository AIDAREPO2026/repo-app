# Deploy

Docker Compose files, the Dockerfile and the Nginx configuration (`P0-OPS-02`), and later the release, rollback and restore scripts (`P4-OPS-01`, `P4-OPS-02`). The same files run staging and production. Secrets come from the `.env` file on each server and are never committed.

| File | What it holds |
| --- | --- |
| `docker-compose.yml` | Every container: `nginx`, `app`, `worker`, `beat`, `tusd`, `seaweedfs`, `clamav`, `postgres`, `redis`. Only `nginx` publishes ports. |
| `docker-compose.dev.yml` | Local development only: the Mailpit mail catcher, with its inbox at http://127.0.0.1:8025 |
| `Dockerfile` | One image with two targets: `app` (FastAPI) and `worker` (adds LibreOffice, FFmpeg and libmagic, used by `worker` and `beat`) |
| `nginx/default.conf` | HTTPS, the security headers, rate limits, the proxy to `app` and to `tusd` at `/files/`, and the internal protected-file location |
| `nginx/make-dev-cert.sh` | Creates a self-signed certificate for `https://localhost` in `nginx/certs/` (not committed) |

## Start the stack locally

```bash
cp .env.example .env
```

Fill in every `change-me` value in `.env`; each line says how to generate it. Then:

```bash
./deploy/nginx/make-dev-cert.sh
```

```bash
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.dev.yml up --build
```

Open https://localhost/healthz and accept the self-signed certificate. If ports 80 and 443 are already taken on your machine, put `HTTP_PORT=8080 HTTPS_PORT=8443` before the command and use https://localhost:8443.

The first start takes several minutes: the worker image installs LibreOffice, and ClamAV downloads its virus signatures.

## Check the security headers

```bash
uv run python scripts/check_headers.py https://localhost --insecure
```

It checks every header in `docs/security.md` and that the internal paths return 404. CI runs it against staging (`P0-OPS-03`).

## Run as root

Two one-shot containers run as root and then exit: `seaweedfs-init` gives the storage folder to the SeaweedFS user, because a new volume or disk is owned by root. ClamAV, PostgreSQL and Redis start as root and switch to their own users, as their official images do. Everything else runs as a non-root user from the start.
