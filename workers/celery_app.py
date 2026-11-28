"""The Celery app that runs background jobs."""

from celery import Celery

from app.core.config import load_config

celery_app = Celery("aida", broker=load_config().redis_url, include=["workers.email"])
# Nobody reads job results, and a queue that is down must not hold a web request for long.
celery_app.conf.update(
    task_ignore_result=True,
    task_publish_retry_policy={"max_retries": 1},
    broker_connection_timeout=2,
)
