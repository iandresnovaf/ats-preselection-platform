"""Evaluation tasks with LLM."""
from app.tasks import celery_app


@celery_app.task(bind=True, max_retries=3)
def evaluate_candidate(self, candidate_id: str, job_id: str):
    """Evaluate a candidate against a job opening using LLM."""
    try:
        # TODO: Implement LLM evaluation
        # 1. Get candidate data
        # 2. Get job requirements
        # 3. Call LLM API
        # 4. Store evaluation results
        return {"status": "completed", "candidate_id": candidate_id}
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
