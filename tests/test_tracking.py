"""
Test event tracking functions.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import copy 
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


@ddt.ddt
class EventTrackingTestCase(CompletionAPITestMixin, TestCase):
    """
    Test that the tracking events are sent/not sent properly and with correct values.
    """

    course_key = CourseKey.from_string('edX/toy/2012_Fall')
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

    @patch('completion_aggregator.tracking.tracker.emit')
    def test_tracking_invalid_event_type(self, mock_emit):
        tracking.track_aggregator_event(self.agg, 'invalid_event')
        mock_emit.assert_not_called()
