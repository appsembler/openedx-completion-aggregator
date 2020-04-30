# -*- coding: utf-8 -*-
"""
Tracking and analytics events for completion aggregator activities.
"""

from eventtracking import tracker

from django.conf import settings

from openedx.core.djangoapps.content.course_structures.models import CourseStructure
from openedx.core.djangoapps.site_configuration import helpers

from . import models


TRACKER_BI_EVENT_NAME_FORMAT = u'edx.bi.user.{agg_type}.{event_type}'
TRACKER_EVENT_NAME_FORMAT = u'edx.completion.aggregator.{event_type}'


def _is_trackable_aggregator_type(block):
    """
    Checks settings to see if we want to track this block type.
    """
    return block.block_type in settings.COMPLETION_AGGREGATOR_TRACKED_BLOCK_TYPES


def track_aggregator_event(user, aggregator_block, event_type):
    """
    Sends a tracking event when a completable aggregator is created
    """

    instance = models.Aggregator.objects.get(user=user, block_key=aggregator_block)

    if event_type == 'started' and instance.percent == 0.0:
        return
    elif event_type == 'completed' and instance.percent != 1.0:
        return

    agg_type = instance.aggregation_name
    block_id = str(instance.block_key)
    course_id = str(instance.course_key)
    percent = instance.percent * 100

    # BI event if we have a SEGMENT integration
    if helpers.get_value('SEGMENT_KEY', None):

        bi_event_name = TRACKER_BI_EVENT_NAME_FORMAT.format(
            agg_type=agg_type,
            event_type=event_type
        )

        try:
            course_struct = CourseStructure.objects.get(course_id=instance.course_key)
            block_name = course_struct.structure['blocks'][block_id]['display_name']
            course_block_id, course_block_struct = course_struct.ordered_blocks.popitem(last=False)
            try:
                assert course_block_struct['block_type'] == 'course'
                course_name = course_block_struct['display_name']
            except AssertionError:  # this shouldn't happen
                course_name = course_id
        except (CourseStructure.DoesNotExist, KeyError):
            course_name = course_id
            block_name = block_id

        tracker.emit(bi_event_name, {
            'label': '{} {} {}'.format(agg_type, block_id, event_type),
            'course_id': course_id,
            'block_id': block_id,
            'completion_percent': percent,
            # these two may only be needed by Chef
            'course_name': course_name,
            'block_name': block_name  # may be a course name
        })

    # generic tracking event
    # TO-DO: need to work on properties and format for non-BI event
    event_name = TRACKER_EVENT_NAME_FORMAT.format(event_type=event_type)
    tracker.emit(event_name, {
        'label': '{} {} {}'.format(agg_type, block_id, event_type),
        'course_id': course_id,
        'block_id': block_id,
        'completion_percent': percent,
    })


def emit_tracking_events(user, aggregator_blocks, event_type):
    """
    Emit tracking events for all tracked aggregator types.
    Emit an event on creation to indicate an Aggregator of completion was "started"
    Emit an event on any save to indicate an Aggregator of completion was completed if percent = 1.0
    """
    # from celery.contrib import rdb; rdb.set_trace()
    # Please telnet 127.0.0.1 6900.  Type `exit` in session to continue.
    # https://docs.celeryproject.org/en/stable/userguide/debugging.html
    if settings.COMPLETION_AGGREGATOR_ENABLE_TRACKING is not True:
        return

    for aggregator_block in aggregator_blocks:
        # created and started could happen together
        if not _is_trackable_aggregator_type(aggregator_block):
            continue
        track_aggregator_event(user, aggregator_block, event_type)
