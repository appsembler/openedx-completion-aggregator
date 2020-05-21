"""
LMS AWS settings for completion_aggregator.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from celery.schedules import crontab
from .aws import plugin_settings as aws_plugin_settings


def plugin_settings(settings):
    """
    Modify the provided settings object with settings specific to this plugin.
    """
    aws_plugin_settings(settings)

    settings.COMPLETION_AGGREGATOR_ENABLE_CELERY_BEAT = set(settings.ENV_TOKENS.get(
        'COMPLETION_AGGREGATOR_ENABLE_CELERY_BEAT',
        settings.COMPLETION_AGGREGATOR_ENABLE_CELERY_BEAT,
    ))

    if settings.COMPLETION_AGGREGATOR_ENABLE_CELERY_BEAT:
        settings.CELERYBEAT_SCHEDULE['completion-aggregator-perform-then-cleanup'] = {
            'task': 'completion_aggregator.tasks.periodic_tasks.perform_then_cleanup',
            'schedule': crontab(
                    # TODO: Make the numbers below configurable.
                    hour=3,
                    minute=0,
                ),
            }
