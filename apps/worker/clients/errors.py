class RetryableError(Exception):
    """Transient failure (rate limit, upstream outage, network): retry the task."""
