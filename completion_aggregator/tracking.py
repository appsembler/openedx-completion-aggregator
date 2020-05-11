# -*- coding: utf-8 -*-
"""
Tracking and analytics events for completion aggregator activities.
"""

from eventtracking import tracker

from . import compat


TRACKER_BI_EVENT_NAME_FORMAT = u'edx.bi.completion.user.{agg_type}.{event_type}'
TRACKER_EVENT_NAME_FORMAT = u'edx.completion.aggregator.{event_type}'
TRACKER_VALID_EVENT_TYPES = {'completed', 'started', 'revoked', }


class TrackingEventTypeError(Exception):
    """
    Raise if aggregator values do not parameters passed to track_aggregation_events.
    """


def track_aggregator_event(aggregator, event_type):
    """
    Emit tracking events for Aggregator changes based on passed event_type

    Emits a "bi"-type event for Segment integration if configured for the Site, with
    additional information including the block and containing course display names.
    Also emits a more generic event for other tracking purposes.

    """

    if event_type not in TRACKER_VALID_EVENT_TYPES:
        return

    event_type_label = 'completion revoked' if event_type == 'revoked' else event_type

    agg_type = aggregator.aggregation_name
    block_id = str(aggregator.block_key)
    course_id = str(aggregator.course_key)
    percent = aggregator.percent * 100
    earned = aggregator.earned
    possible = aggregator.possible

    # BI event if we have a SEGMENT integration
    if compat.get_segment_key():
        bi_event_name = TRACKER_BI_EVENT_NAME_FORMAT.format(
            agg_type=agg_type,
            event_type=event_type
        )

        # get the display names out of the CourseStructure for efficiency
        try:
            course_struct = compat.coursestructure_model().objects.get(course_id=aggregator.course_key)
            block_name = course_struct.structure['blocks'][block_id]['display_name']
            _, course_block_struct = course_struct.ordered_blocks.popitem(last=False)
            try:
                assert course_block_struct['block_type'] == 'course'
                course_name = course_block_struct['display_name']
            except AssertionError:  # this shouldn't happen
                course_name = course_id
        except (compat.coursestructure_model().DoesNotExist, KeyError):
            course_name = course_id
            block_name = block_id

        tracker.emit(bi_event_name, {
            'label': '{} {} {}'.format(agg_type, block_name, event_type_label),
            'course_id': course_id,
            'block_id': block_id,
            'completion_percent': percent,
            'course_name': course_name,
            'block_name': block_name,
        })

    # generic tracking event
    event_name = TRACKER_EVENT_NAME_FORMAT.format(event_type=event_type)
    label_id = course_id if agg_type == 'course' else block_id
    tracker.emit(event_name, {
        'label': '{} {} {}'.format(agg_type, label_id, event_type_label),
        'course_id': course_id,
        'block_id': block_id,
        'completion_percent': percent,
        'completion_earned': earned,
        'completion_possible': possible,
        'block_type': agg_type,
    })


def track_aggregation_events(aggregator, is_new=False, completion_revoked=False):
    """
    If event tracking feature is enabled and is a trackable type, call function to emit tracking events.
    Validate that the properties of the aggregator match revocation param.
    Keep in mind that the aggregator may not have been saved to the database yet.
    """
    if not compat.is_tracking_enabled():
        return
    if aggregator.aggregation_name not in compat.get_trackable_aggregator_types():
        return
    if aggregator.percent == 0:
        return
    if completion_revoked and aggregator.percent == 1.0:
        raise TrackingEventTypeError("Can't revoke a completion with a 100% complete.")

    event_types = []

    if is_new:
        event_types.append('started')
    if aggregator.percent == 1.0:
        event_types.append('completed')
    elif completion_revoked:
        event_types.append('revoked')
    for event_type in event_types:
        track_aggregator_event(aggregator, event_type)
