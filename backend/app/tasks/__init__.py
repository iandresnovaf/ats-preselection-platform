"""Celery configuration and tasks."""
from celery import Celery
from celery.signals import task_failure
import logging

from app.core.config import settings

# Configure Celery
celery_app = Celery(
    "ats_platform",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.cv_processing",
        "app.tasks.evaluation",
        "app.tasks.notifications",
        "app.tasks.sync",
        "app.tasks.rhtools",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Task routing
celery_app.conf.task_routes = {
    "app.tasks.cv_processing.*": {"queue": "cv_processing"},
    "app.tasks.evaluation.*": {"queue": "evaluation"},
    "app.tasks.notifications.*": {"queue": "notifications"},
    "app.tasks.sync.*": {"queue": "sync"},
    "app.tasks.rhtools.*": {"queue": "cv_processing"},
}

# Retry configuration
celery_app.conf.task_default_retry_delay = 60  # 1 minute
celery_app.conf.task_max_retries = 3


@task_failure.connect
def handle_task_failure(task_id, exception, args, kwargs, traceback, einfo, **extras):
    """Handle task failures."""
    logging.error(f"Task {task_id} failed: {exception}")
    # TODO: Send notification to admin
    # TODO: Store failure in database for retry


@celery_app.task(bind=True, max_retries=3)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")
    return {"status": "ok", "task_id": self.request.id}
