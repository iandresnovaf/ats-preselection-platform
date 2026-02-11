"""Zoho sync tasks."""
from app.tasks import celery_app


@celery_app.task(bind=True, max_retries=5)
def sync_candidate_to_zoho(self, candidate_id: str):
    """Sync candidate to Zoho Recruit."""
    try:
        # TODO: Implement Zoho sync
        return {"status": "synced", "candidate_id": candidate_id}
    except Exception as exc:
        self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=5)
def sync_job_to_zoho(self, job_id: str):
    """Sync job opening to Zoho Recruit."""
    try:
        # TODO: Implement Zoho sync
        return {"status": "synced", "job_id": job_id}
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
