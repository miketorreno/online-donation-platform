"""Tests for Celery background tasks (foundation).

Tasks are executed synchronously via `.apply()` (eager) so they can be tested
without a live broker/worker.
"""
from django.test import SimpleTestCase

from core.tasks import ping


class PingTaskTests(SimpleTestCase):
    def test_ping_returns_pong(self):
        result = ping.apply(args=["hello"])
        self.assertEqual(result.get(), "pong:hello")

    def test_ping_without_payload(self):
        result = ping.apply()
        self.assertEqual(result.get(), "pong:")
