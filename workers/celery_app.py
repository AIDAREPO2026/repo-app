"""The Celery app that runs background jobs. Jobs are added from P2-UPL-03 onwards."""

from celery import Celery

from app.core.config import load_config

celery_app = Celery("aida", broker=load_config().redis_url)
