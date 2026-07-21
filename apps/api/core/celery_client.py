from celery import Celery

from core.config import settings

celery_client = Celery("trupitch-api", broker=settings.redis_url)

celery_client.conf.update(
    task_serializer="json",
    accept_content=["json"],
    broker_connection_retry_on_startup=False,
    broker_transport_options={"max_retries": 1},
)
