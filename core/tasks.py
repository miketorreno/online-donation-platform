"""Celery background tasks for the core app.

Tasks must be idempotent and accept primary keys (never ORM instances), since
they may execute asynchronously after the request that enqueued them.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="core.ping")
def ping(payload: str = "") -> str:
    """Smoke-test task proving the broker/worker round-trip works."""
    logger.info("core.ping received payload=%r", payload)
    return f"pong:{payload}"
