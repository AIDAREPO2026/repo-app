# Deploy

Docker Compose files, the Dockerfile and the Nginx configuration (`P0-OPS-02`), and later the release, rollback and restore scripts (`P4-OPS-01`, `P4-OPS-02`). The same files run staging and production. Secrets come from the `.env` file on each server and are never committed.

| File | What it holds |
| --- | --- |
| `docker-compose.yml` | Every container: `nginx`, `app`, `worker`, `beat`, `tusd`, `seaweedfs`, `clamav`, `postgres`, `redis`. Only `nginx` publishes ports. |
| `docker-compose.dev.yml` | Local development only: the portal over plain HTTP at http://localhost:8081, the Mailpit inbox at http://127.0.0.1:8025, and the SeaweedFS file browser at http://127.0.0.1:8888 to see stored files. All are reachable from this machine only; the inbox and file browser have no login. |
| `Dockerfile` | One image with two targets: `app` (FastAPI) and `worker` (adds LibreOffice, FFmpeg and libmagic, used by `worker` and `beat`) |
| `nginx/default.conf` | HTTPS, rate limits, and the redirect from HTTP |
| `nginx/snippets/portal-routes.conf` | Everything the portal serves: the security headers, the proxy to `app` and to `tusd` at `/files/`, and the internal protected-file location |
| `nginx/local-http.conf` | Local development only: the same routes over plain HTTP on port 8081, mounted by `docker-compose.dev.yml` |
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

Open http://localhost:8081. The dev file serves the portal there over plain HTTP, through the same Nginx routes, limits and security headers (`nginx/local-http.conf`), so no certificate is needed; browsers accept the Secure session cookie on `localhost`. HTTPS still runs at https://localhost/healthz with the self-signed certificate, for checking TLS and the headers. If ports 80 and 443 are already taken on your machine, put `HTTP_PORT=8080 HTTPS_PORT=8443` before the command and use https://localhost:8443.

The first start takes several minutes: the worker image installs LibreOffice, and ClamAV downloads its virus signatures.

## Where the data lives

The database and stored files are **not** kept in Docker volumes. They live in host folders under `DATA_DIR`:

| Folder | What it holds |
| --- | --- |
| `$DATA_DIR/postgres` | The PostgreSQL database |
| `$DATA_DIR/seaweedfs` | Every stored file (SeaweedFS) |

Removing containers, rebuilding images or running `docker compose down -v` never deletes them. Locally `DATA_DIR` defaults to the git-ignored `data/` folder. On a server it is a folder on the encrypted data disk, such as `/srv/aida` (`P0-OPS-01`), and Compose runs from the repository root with the root `.env`:

```bash
docker compose --env-file .env -f deploy/docker-compose.yml up -d
```

**Never run `down -v` on a server.** It no longer deletes the data, but it still wipes the Redis queues and ClamAV signatures, and there is no reason to use it there. Releases and rollbacks use only `deploy/release.sh` and `deploy/rollback.sh` (`P4-OPS-02`). The nightly backups in `P4-OPS-01` copy both folders off the server.

Redis and ClamAV keep Docker volumes, because losing them loses only short-lived queues, counters and virus signatures, which download again.

To start completely fresh on a laptop, stop the stack and delete `data/`.

## Who can reach the file storage

SeaweedFS sits only on the `storage` network, which only `app`, `worker`, `tusd` and `nginx` join. PostgreSQL, Redis, ClamAV and `beat` cannot reach it at all. Its S3 port accepts only requests signed with the keys in `.env`, and none of its ports is published on a server. To look at stored files on a server, use an SSH tunnel or `weed shell` over SSH, never an open port.

## Check the security headers

```bash
uv run python scripts/check_headers.py https://localhost --insecure
```

It checks every header in `docs/security.md` and that the internal paths return 404. CI runs it against staging (`P0-OPS-03`).

## Run as root

Two one-shot containers run as root and then exit: `seaweedfs-init` gives the storage folder to the SeaweedFS user, because a new volume or disk is owned by root. ClamAV, PostgreSQL and Redis start as root and switch to their own users, as their official images do. Everything else runs as a non-root user from the start.
