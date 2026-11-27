# Workers

Celery background jobs: virus scanning, Office previews, text extraction, emails and scheduled jobs. `celery_app.py` holds the Celery app, added early so the `worker` and `beat` containers run (`P0-OPS-02`). Jobs and the beat schedule arrive with the first job (`P2-UPL-03`). Job functions call module `service.py` functions rather than holding business rules themselves.
