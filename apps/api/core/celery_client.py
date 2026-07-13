"""Dispatch-only Celery client.

The API never imports worker code; tasks are addressed by name via
`send_task`, keeping the ingestion layer isolated from the worker
implementation.
"""

from celery import Celery

from core.config import settings

celery_client = Celery("trupitch-api", broker=settings.redis_url)

celery_client.conf.update(
    task_serializer="json",
    accept_content=["json"],
    # Fail fast if the broker is down instead of hanging the HTTP request.
    broker_connection_retry_on_startup=False,
    broker_transport_options={"max_retries": 1},
)
