"""Notification tasks (WhatsApp, Email)."""
from app.tasks import celery_app


@celery_app.task(bind=True, max_retries=5)
def send_whatsapp_message(self, communication_id: str):
    """Send WhatsApp message."""
    try:
        # TODO: Implement WhatsApp sending
        return {"status": "sent", "communication_id": communication_id}
    except Exception as exc:
        self.retry(exc=exc, countdown=300)  # 5 minutes


@celery_app.task(bind=True, max_retries=3)
def send_email(self, communication_id: str):
    """Send email."""
    try:
        # TODO: Implement email sending
        return {"status": "sent", "communication_id": communication_id}
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
