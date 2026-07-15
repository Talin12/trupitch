"""Dispatch-only Celery client.

The API never imports worker code; tasks are addressed by name via
`send_task`, keeping the ingestion layer isolated from the worker
implementation. This means the API process needs no knowledge of
`apps/worker` at all — if the worker's internals change, nothing here
has to change as long as the task name ("evaluate_submission") and its
argument signature stay the same.
"""

from celery import Celery

from core.config import settings

# A Celery app whose only job is to *publish* tasks onto the broker
# (Redis). It never registers a task or runs a worker loop — that's
# apps/worker/tasks.py's job, running as a completely separate process.
celery_client = Celery("trupitch-api", broker=settings.redis_url)

celery_client.conf.update(
    task_serializer="json",
    accept_content=["json"],
    # Fail fast if the broker is down instead of hanging the HTTP request.
    # Without this, Celery's default behavior is to retry connecting to
    # the broker in a loop, which would block the ingestion endpoint for
    # a long time instead of surfacing a clear 503 to the client.
    broker_connection_retry_on_startup=False,
    broker_transport_options={"max_retries": 1},
)
