"""
Tasks for the CeleryBeat scheduler.
"""

from celery.app.base import Celery

from ..batch import (
    perform_cleanup,
    perform_aggregation,
)


@Celery.task
def perform_then_cleanup():
    perform_aggregation()
    perform_cleanup()
