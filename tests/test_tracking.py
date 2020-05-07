"""
Test event tracking functions.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

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

    # @XBlock.register_temp_plugin(StubCourse, 'course')
    # @XBlock.register_temp_plugin(StubSequential, 'sequential')
    # @XBlock.register_temp_plugin(StubHTML, 'html')
    # def test_detail_view_staff_requested_multiple_users(self):
    #     """
    #     Test that requesting course completions for a set of users filters out the other enrolled users
    #     """
    #     version = 1
    #     users = self.create_enrolled_users(3)
    #     self.create_course_completion_data(users[0], 3.0, 12.0)
    #     self.create_course_completion_data(users[1], 9.0, 12.0)
    #     self.create_course_completion_data(users[2], 6.0, 12.0)
    #     self.client.force_authenticate(self.staff_user)
    #     user_ids = "{},{}".format(users[0].id, users[2].id)
    #     response = self.client.get(self.get_detail_url(version, self.course_key, user_ids=user_ids))
    #     self.assertEqual(response.status_code, 200)
    #     expected_values = [
    #         {
    #             'username': users[0].username,
    #             'course_key': 'edX/toy/2012_Fall',
    #             'completion': self._get_expected_completion(1, earned=3.0, possible=12.0, percent=0.25),
    #         },
    #         {
    #             'username': users[2].username,
    #             'course_key': 'edX/toy/2012_Fall',
    #             'completion': self._get_expected_completion(1, earned=6.0, possible=12.0, percent=0.5),
    #         },
    #     ]
    #     expected = self._get_expected_detail(version, expected_values, count=2)
    #     self.assertEqual(response.data, expected)
