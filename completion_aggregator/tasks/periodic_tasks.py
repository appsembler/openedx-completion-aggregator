"""
Tasks for the CeleryBeat scheduler.
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from celery import shared_task
from celery_utils.logged_task import LoggedTask


from ..batch import (
    perform_cleanup,
    perform_aggregation,
)


@shared_task(task=LoggedTask)
def perform_then_cleanup():
    if not settings.COMPLETION_AGGREGATOR_ASYNC_AGGREGATION:
        raise ImproperlyConfigured(
            'Completion Aggregator configuration error: Both COMPLETION_AGGREGATOR_ASYNC_AGGREGATION is a'
            'pre-requisite for COMPLETION_AGGREGATOR_ENABLE_CELERY_BEAT to avoid duplicate processing.'
        )

    perform_aggregation()
    perform_cleanup()
