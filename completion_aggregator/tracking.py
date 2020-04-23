# -*- coding: utf-8 -*-
"""
Tracking and analytics events for completion aggregator activities.
"""

from datetime import datetime

from eventtracking import tracker

from django.conf import settings

from openedx.core.djangoapps.site_configuration import helpers



TRACKER_BI_EVENT_NAME_FORMAT = u'edx.bi.user.{agg_type}.{event_type}'
TRACKER_EVENT_NAME_FORMAT = u'edx.completion.aggregator.{event_type}'


def _is_trackable_aggregator_type(instance):
    """
    Checks settings to see if we want to track this block type.
    """
    return instance.aggregation_name in settings.COMPLETION_AGGREGATOR_TRACKED_BLOCK_TYPES


def track_aggregator_event(instance, event_type):
    """
    Sends a tracking event when a completable aggregator is created
    """
    if not _is_trackable_aggregator_type(instance):
        return

    agg_type = instance.aggregation_name
    block_id = instance.block_key.to_string()
    course_id = instance.course_key.to_string()
    user_id = instance.user.id
    timestamp = str(datetime.now())
    percent = instance.percent * 100

    # BI event if we have a SEGMENT integration
    if helpers.get_value('SEGMENT_KEY', None):

        bi_event_name = TRACKER_BI_EVENT_NAME_FORMAT.format(
            agg_type=agg_type,
            event_type=event_type
        )

        # TODO: transform this event to add course_name and block_name
        # those probably aren't of interest except for Chef (?)
        # so maybe use a common.djangoapps.track.transformers.EventTransformer ?
        tracker.emit(
            user_id,
            bi_event_name,
            {
                'label': '{} {} {}'.format(agg_type, block_id, event_type),
                'course_id': course_id,
                'block_id': block_id,
                'timestamp': timestamp,
                'completion_percent': percent,
            },
        )

    # generic tracking event
    # need to work on properties and format for non-BI event
    event_name = TRACKER_EVENT_NAME_FORMAT.format(event_type)
    tracker.emit(
        user_id,
        event_name,
        {
            'label': '{} {} {}'.format(agg_type, block_id, event_type),
            'course_id': course_id,
            'block_id': block_id,
            'timestamp': timestamp,
            'completion_percent': percent,
        },
    )
