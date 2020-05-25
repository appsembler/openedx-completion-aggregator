"""
Test event tracking functions.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from copy import copy
import ddt
from mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils.timezone import now

from opaque_keys.edx.keys import CourseKey

from completion_aggregator import models, tracking

from test_utils.compat import StubCompat
from test_utils.test_mixins import CompletionAPITestMixin


empty_compat = StubCompat([])


EXPECTED_EVENT_DATA_GENERIC_STARTED = {
    'label': 'course course-v1:Appsembler+AggEvents101+2020 started',
    'course_id': 'course-v1:Appsembler+AggEvents101+2020',
    'block_id': 'block-v1:Appsembler+AggEvents101+2020+type@course+block@course',
    'block_type': 'course',
    'completion_percent': 10.0,
    'completion_earned': 0.1,
    'completion_possible': 1.0,
    'org': 'Appsembler',
    'context': {'user_id': 1}
}

EXPECTED_EVENT_DATA_GENERIC_COMPLETED = copy(EXPECTED_EVENT_DATA_GENERIC_STARTED)
EXPECTED_EVENT_DATA_GENERIC_COMPLETED.update({
    'label': 'course course-v1:Appsembler+AggEvents101+2020 completed',
    'completion_percent': 100.0,
    'completion_earned': 1.0,
})

EXPECTED_EVENT_DATA_GENERIC_REVOKED = copy(EXPECTED_EVENT_DATA_GENERIC_COMPLETED)
EXPECTED_EVENT_DATA_GENERIC_REVOKED.update({
    'label': 'course course-v1:Appsembler+AggEvents101+2020 completion revoked',
    'completion_percent': 90.0,
    'completion_earned': 0.9,
})

EXPECTED_EVENT_DATA_BI_STARTED = copy(EXPECTED_EVENT_DATA_GENERIC_STARTED)
EXPECTED_EVENT_DATA_BI_STARTED.update({
    'label': 'course Appsembler Aggregation Events 101 started',
    'course_name': 'Appsembler Aggregation Events 101',
    'block_name': 'Appsembler Aggregation Events 101',
    'email': ''
})

EXPECTED_EVENT_DATA_BI_COMPLETED = copy(EXPECTED_EVENT_DATA_GENERIC_COMPLETED)
EXPECTED_EVENT_DATA_BI_COMPLETED.update({
    'label': 'course Appsembler Aggregation Events 101 completed',
    'course_name': 'Appsembler Aggregation Events 101',
    'block_name': 'Appsembler Aggregation Events 101',
    'email': ''
})

EXPECTED_EVENT_DATA_BI_REVOKED = copy(EXPECTED_EVENT_DATA_GENERIC_REVOKED)
EXPECTED_EVENT_DATA_BI_REVOKED.update({
    'label': 'course Appsembler Aggregation Events 101 completion revoked',
    'course_name': 'Appsembler Aggregation Events 101',
    'block_name': 'Appsembler Aggregation Events 101',
    'email': ''
})

# bi events don't need as much detail
for key in ('completion_earned', 'completion_possible', 'block_type'):
    del EXPECTED_EVENT_DATA_BI_STARTED[key]
    del EXPECTED_EVENT_DATA_BI_COMPLETED[key]


@ddt.ddt
@override_settings(COMPLETION_AGGREGATOR_ENABLE_TRACKING=True)
class EventTrackingTestCase(CompletionAPITestMixin, TestCase):
    """
    Test that the tracking events are sent/not sent properly and with correct values.
    """

    course_key = CourseKey.from_string('course-v1:Appsembler+AggEvents101+2020')
    course_block_key = course_key.make_usage_key('course', 'course')
    course_enrollment_model = empty_compat.course_enrollment_model()

    def setUp(self):
        super(EventTrackingTestCase, self).setUp()
        self.test_user = User.objects.create(username='test_user')
        self.agg, _ = models.Aggregator.objects.submit_completion(
            user=self.test_user,
            course_key=self.course_key,
            block_key=self.course_block_key,
            aggregation_name='course',
            earned=0.0,
            possible=1.0,
            last_modified=now(),
        )
        # update with correct user id
        for event in (
            EXPECTED_EVENT_DATA_GENERIC_STARTED,
            EXPECTED_EVENT_DATA_GENERIC_COMPLETED,
            EXPECTED_EVENT_DATA_GENERIC_REVOKED,
            EXPECTED_EVENT_DATA_BI_STARTED,
            EXPECTED_EVENT_DATA_BI_COMPLETED,
            EXPECTED_EVENT_DATA_BI_REVOKED
        ):
            event['context']['user_id'] = self.test_user.id

        for compat_import in (
                'completion_aggregator.tracking.compat',
                'completion_aggregator.compat',
        ):
            patcher = patch(compat_import, empty_compat)
            patcher.start()
            self.addCleanup(patcher.__exit__, None, None, None)

    @override_settings(COMPLETION_AGGREGATOR_ENABLE_TRACKING=False)
    @patch('completion_aggregator.tracking.track_aggregator_event')
    def test_no_tracking_if_disabled(self, mock_track_aggregator_event):
        tracking.track_aggregation_events(self.agg)
        assert mock_track_aggregator_event.call_count == 0

    @override_settings(COMPLETION_AGGREGATOR_ENABLE_TRACKING=True)
    @override_settings(COMPLETION_AGGREGATOR_TRACKED_BLOCK_TYPES=['chapter', ])
    @patch('completion_aggregator.tracking.track_aggregator_event')
    def test_tracking_if_enabled(self, mock_track_aggregator_event):
        tracking.track_aggregation_events(self.agg)
        assert mock_track_aggregator_event.call_count == 0

    @ddt.data((0.0, True), (0.0, False), (1.0, True), (1.0, False), (0.1, True), (0.1, False))
    @ddt.unpack
    @patch('completion_aggregator.tracking.track_aggregator_event')
    def test_tracking_completed_by_earned_and_newness(self, percent, is_new, mock_track_aggregator_event):
        self.agg.percent = percent
        tracking.track_aggregation_events(self.agg, is_new)
        if percent == 0:
            mock_track_aggregator_event.assert_not_called()
        elif percent == 1:
            mock_track_aggregator_event.assert_any_call(self.agg, 'completed')
        elif percent < 1 and is_new:
            mock_track_aggregator_event.assert_called_once_with(self.agg, 'started')
        elif percent < 1 and not is_new:
            mock_track_aggregator_event.assert_not_called()

    @patch('completion_aggregator.tracking.track_aggregator_event')
    def test_tracking_valid_invalid_completion_revoked(self, mock_track_aggregator_event):
        self.agg.percent = 1.0
        with self.assertRaises(tracking.TrackingEventTypeError):
            tracking.track_aggregation_events(self.agg, is_new=False, completion_revoked=True)
        mock_track_aggregator_event.reset_mock()
        self.agg.percent = 0.9
        tracking.track_aggregation_events(self.agg, is_new=False, completion_revoked=True)
        mock_track_aggregator_event.assert_any_call(self.agg, 'revoked')

    @patch('completion_aggregator.tracking.tracker.emit')
    def test_tracking_invalid_event_type(self, mock_emit):
        tracking.track_aggregator_event(self.agg, 'invalid_event')
        mock_emit.assert_not_called()

    @override_settings(SEGMENT_KEY=None)
    @patch('completion_aggregator.tracking.tracker.emit')
    def test_tracking_no_bi_event_if_no_segment_key(self, mock_emit):
        tracking.track_aggregator_event(self.agg, 'started')
        mock_emit.assert_called_once()

    @ddt.data('started', 'completed')
    @patch('completion_aggregator.tracking.tracker.emit')
    def test_tracking_events_course_happy_path(self, event_type, mock_emit):
        if event_type == 'started':
            self.agg.earned = self.agg.percent = 0.1
            tracking.track_aggregator_event(self.agg, event_type)
            mock_emit.assert_any_call('edx.bi.completion.user.course.started', EXPECTED_EVENT_DATA_BI_STARTED)
            mock_emit.assert_any_call('edx.completion.aggregator.started', EXPECTED_EVENT_DATA_GENERIC_STARTED)
        elif event_type == 'completed':
            self.agg.earned = self.agg.percent = 1.0
            tracking.track_aggregator_event(self.agg, event_type)
            mock_emit.assert_any_call('edx.bi.completion.user.course.completed', EXPECTED_EVENT_DATA_BI_COMPLETED)
            mock_emit.assert_any_call('edx.completion.aggregator.completed', EXPECTED_EVENT_DATA_GENERIC_COMPLETED)
        elif event_type == 'revoked':
            self.agg.earned = self.agg.percent = 0.9
            tracking.track_aggregator_event(self.agg, event_type)
            mock_emit.assert_any_call('edx.bi.completion.user.course.revoked', EXPECTED_EVENT_DATA_BI_REVOKED)
            mock_emit.assert_any_call('edx.completion.aggregator.revoked', EXPECTED_EVENT_DATA_GENERIC_REVOKED)
