# -*- coding: utf-8 -*-
"""
Tracking and analytics events for completion aggregator activities.
"""

import analytics

from django.conf import settings

# from eventtracking import tracker
# # from track import contexts
# from track.event_transaction_utils import (
#     create_new_event_transaction_id,
#     get_event_transaction_id,
#     get_event_transaction_type,
#     set_event_transaction_type
# )


TRACKER_BI_STARTED_EVENT_NAME_FORMAT = u'edx.bi.user.{type}.started'
TRACKER_BI_COMPLETED_EVENT_NAME_FORMAT = u'edx.bi.user.{type}.completed'
TRACKER_STARTED_EVENT_NAME = u'edx.completion.aggregator.started'
TRACKER_COMPLETED_EVENT_NAME = u'edx.completion.aggregator.completed'


def _is_trackable_aggregator_type(instance):
    """
    Checks settings to see if we want to track this block type.
    """
    return instance.aggregation_name in settings.COMPLETION_AGGREGATOR_TRACKED_BLOCK_TYPES


def track_aggregator_start(instance):
    """
    Sends a tracking event when a completable aggregator is created
    """
    if not _is_trackable_aggregator_type(instance):
        return

    # BI event if we have a SEGMENT integration
    if hasattr(settings, 'LMS_SEGMENT_KEY') and settings.LMS_SEGMENT_KEY:

        bi_event_name = TRACKER_BI_STARTED_EVENT_NAME_FORMAT.format(type=instance.aggregation_name)

        tracking_context = tracker.get_tracker().resolve_context()
        analytics.track(
            instance.user.id,
            "edx.bi.user.account.authenticated",
            {
                'category': "conversion",
                'label': request.POST.get('course_id'),
                'provider': None
            },
            context={
                'ip': tracking_context.get('ip'),
                'Google Analytics': {
                    'clientId': tracking_context.get('client_id')
                }
            }
        )

    # generic tracking event

    event_name = TRACKER_STARTED_EVENT_NAME
    
    context = contexts.course_context_from_course_id(subsection_grade.course_id)
    # TODO (AN-6134): remove this context manager
    with tracker.get_tracker().context(event_name, context):
        tracker.emit(
            event_name,
            {
                'user_id': unicode(subsection_grade.user_id),
                'course_id': unicode(subsection_grade.course_id),
                'block_id': unicode(subsection_grade.usage_key),
                'course_version': unicode(subsection_grade.course_version),
                'weighted_total_earned': subsection_grade.earned_all,
                'weighted_total_possible': subsection_grade.possible_all,
                'weighted_graded_earned': subsection_grade.earned_graded,
                'weighted_graded_possible': subsection_grade.possible_graded,
                'first_attempted': unicode(subsection_grade.first_attempted),
                'subtree_edited_timestamp': unicode(subsection_grade.subtree_edited_timestamp),
                'event_transaction_id': unicode(get_event_transaction_id()),
                'event_transaction_type': unicode(get_event_transaction_type()),
                'visible_blocks_hash': unicode(subsection_grade.visible_blocks_id),
            }
        )