# Workers

Celery background jobs: virus scanning, Office previews, text extraction, emails and scheduled jobs. `celery_app.py` holds the Celery app, added early so the `worker` and `beat` containers run (`P0-OPS-02`). The first job is email delivery with retries (`email.py`, `P1-ACC-03`); the web app renders the message and queues it. The beat schedule arrives with the first scheduled job. Job functions call module `service.py` functions rather than holding business rules themselves.
