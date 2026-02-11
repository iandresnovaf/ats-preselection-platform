"""CV processing tasks."""
from app.tasks import celery_app


@celery_app.task(bind=True, max_retries=3)
def process_cv(self, cv_id: str):
    """Process a CV: extract data, evaluate, etc."""
    try:
        # TODO: Implement CV processing
        # 1. Parse CV
        # 2. Extract structured data
        # 3. Detect duplicates
        # 4. Queue for evaluation
        return {"status": "completed", "cv_id": cv_id}
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
