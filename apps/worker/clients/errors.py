class RetryableError(Exception):
    """Transient failure (rate limit, upstream outage, network): retry the task.

    Raised by clients/github.py and clients/llm.py whenever a failure
    looks temporary rather than permanent. tasks.py registers this
    exception type in `autoretry_for`, so raising it anywhere inside the
    pipeline causes Celery to automatically retry the whole
    evaluate_submission task with exponential backoff, instead of the
    task failing outright.
    """
