# One Dockerfile, two targets, so app and worker share the same Python layer:
#   app:    docker build --target app -f deploy/Dockerfile .
#   worker: docker build --target worker -f deploy/Dockerfile .
# Builds the portal CSS with Tailwind. Only app.css leaves this stage, so no Node reaches the servers.
FROM node:24.22.3-alpine3.24 AS css
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY app/templates ./app/templates
COPY app/static/css/app.src.css ./app/static/css/
RUN npm run build:css


FROM python:3.12.16-slim-trixie AS base

COPY --from=ghcr.io/astral-sh/uv:0.13.10 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH

WORKDIR /srv/app

# Dependencies first, so code changes do not reinstall them.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
COPY --from=css /build/app/static/css/app.css ./app/static/css/app.css
COPY workers ./workers

# Fixed uid and gid 10001 so every container agrees who owns the files volume (D-14).
RUN groupadd --system --gid 10001 aida \
    && useradd --system --uid 10001 --gid aida --no-create-home aida


FROM base AS app
USER aida
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request, sys; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status != 200)"]
# Nginx is the only proxy in front, so its X-Forwarded-* headers are trusted.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers", "--forwarded-allow-ips", "*"]


FROM base AS worker
# LibreOffice for Office previews, FFmpeg for media metadata, libmagic for file-type sniffing.
USER root
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libreoffice-nogui ffmpeg libmagic1 \
    && rm -rf /var/lib/apt/lists/*
USER aida
CMD ["celery", "--app", "workers.celery_app", "worker", "--loglevel", "INFO"]
