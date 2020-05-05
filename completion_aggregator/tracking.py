# -*- coding: utf-8 -*-
"""
Tracking and analytics events for completion aggregator activities.
"""

from eventtracking import tracker

from . import compat, models


TRACKER_BI_EVENT_NAME_FORMAT = u'edx.bi.user.{agg_type}.{event_type}'
TRACKER_EVENT_NAME_FORMAT = u'edx.completion.aggregator.{event_type}'


def _is_trackable_aggregator_type(block):
    """
    Checks settings to see if we want to track this aggregator(block) type.
    """
    return block.block_type in compat.get_trackable_aggregator_types()


def track_aggregator_event(user, aggregator_block, event_type):
    """
    Emit tracking events for Aggregator changes based on settings and param event_type.

    Takes an event type of 'started' or 'completed'.  Validates completion percentage
    matches passed event_type.

    Emits a "bi"-type event for Segment integration if configured for the Site, with
    additional information including the block and containing course display names.
    Also emits a more generic event for other tracking purposes.

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
    earned = instance.earned
    possible = instance.possible

    # BI event if we have a SEGMENT integration
    if compat.get_segment_key() is not None:

        bi_event_name = TRACKER_BI_EVENT_NAME_FORMAT.format(
            agg_type=agg_type,
            event_type=event_type
        )

        # get the display names out of the CourseStructure for efficiency
        try:
            course_struct = compat.coursestructure_model.objects.get(course_id=instance.course_key)
            block_name = course_struct.structure['blocks'][block_id]['display_name']
            course_block_id, course_block_struct = course_struct.ordered_blocks.popitem(last=False)
            try:
                assert course_block_struct['block_type'] == 'course'
                course_name = course_block_struct['display_name']
            except AssertionError:  # this shouldn't happen
                course_name = course_id
        except (compat.coursestructure_model.DoesNotExist, KeyError):
            course_name = course_id
            block_name = block_id

        tracker.emit(bi_event_name, {
            'label': '{} {} {}'.format(agg_type, block_name, event_type),
            'course_id': course_id,
            'block_id': block_id,
            'completion_percent': percent,
            'course_name': course_name,
            'block_name': block_name,
        })

    # generic tracking event
    event_name = TRACKER_EVENT_NAME_FORMAT.format(event_type=event_type)
    tracker.emit(event_name, {
        'label': '{} {} {}'.format(agg_type, block_id, event_type),
        'course_id': course_id,
        'block_id': block_id,
        'completion_percent': percent,
        'completion_earned': earned,
        'completion_possible': possible,
        'block_type': agg_type,
    })


def track_aggregation_events(user, aggregator_blocks, event_type):
    """
    If event tracking feature is enabled, call function to emit tracking events.
    """
    if compat.is_tracking_enabled() is not True:
        return
    emit_tracking_events(user, aggregator_blocks, event_type)


def emit_tracking_events(user, aggregator_blocks, event_type):
    """
    Emit tracking events for all tracked aggregator types.
    """
    for aggregator_block in aggregator_blocks:
        # created and started could happen together
        if not _is_trackable_aggregator_type(aggregator_block):
            continue
        track_aggregator_event(user, aggregator_block, event_type)
