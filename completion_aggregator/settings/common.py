"""
Common settings for completion_aggregator.
"""

from __future__ import absolute_import, division, print_function, unicode_literals


def plugin_settings(settings):
    """
    Modify the provided settings object with settings specific to this plugin.
    """
    settings.COMPLETION_AGGREGATOR_BLOCK_TYPES = {
        'course',
        'chapter',
        'sequential',
        'vertical',
    }
    settings.COMPLETION_AGGREGATOR_ASYNC_AGGREGATION = False
    settings.COMPLETION_AGGREGATOR_ENABLE_TRACKING = False
    settings.COMPLETION_AGGREGATOR_TRACKED_BLOCK_TYPES = ['course', 'chapter', ]
