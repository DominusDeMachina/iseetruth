from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery("osint")
celery_app.conf.update(
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
)
celery_app.autodiscover_tasks(["app.worker"], related_name="tasks.process_document")
