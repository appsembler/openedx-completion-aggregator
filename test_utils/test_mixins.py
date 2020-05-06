from mock import patch

from django.contrib.auth.models import User
from django.utils import timezone

from completion.models import BlockCompletion
from completion_aggregator import models
from .compat import StubCompat


class CompletionAPITestMixin(object):
    """
    Common utility functions for completion tests
    """

    @property
    def course_enrollment_model(self):
        return StubCompat([]).course_enrollment_model()

    def patch_object(self, obj, method, **kwargs):
        """
        Patch an object for the lifetime of the given test.
        """
        patcher = patch.object(obj, method, **kwargs)
        patcher.start()

        self.addCleanup(patcher.__exit__, None, None, None)
        return patcher

    def mark_completions(self):
        """
        Create completion data to test against.
        """
        BlockCompletion.objects.create(
            user=self.test_user,
            course_key=self.course_key,
            block_key=self.blocks[3],
            block_type='html',
            completion=1.0,
        )
        models.StaleCompletion.objects.update(resolved=True)
        models.Aggregator.objects.submit_completion(
            user=self.test_user,
            course_key=self.course_key,
            block_key=self.course_key.make_usage_key(block_type='sequential', block_id='course-sequence1'),
            aggregation_name='sequential',
            earned=1.0,
            possible=5.0,
            last_modified=timezone.now(),
        )

        models.Aggregator.objects.submit_completion(
            user=self.test_user,
            course_key=self.course_key,
            block_key=self.course_key.make_usage_key(block_type='course', block_id='course'),
            aggregation_name='course',
            earned=1.0,
            possible=8.0,
            last_modified=timezone.now(),
        )

    def create_enrollment(self, user, course_id):
        """
        create a CourseEnrollment.
        """
        return self.course_enrollment_model.objects.create(
            user=user,
            course_id=course_id,
        )

    def create_enrolled_users(self, count):
        """
        Create 'count' number of enrolled users.
        """
        users = []
        for user_id in range(count):
            username = 'user{}'.format(user_id)
            user = User.objects.create(username=username)
            users.append(user)
            self.create_enrollment(
                user=user,
                course_id=self.course_key,
            )
        return users

    def create_course_completion_data(self, user, earned, possible):
        """
        Create course-level completion data.
        """
        models.Aggregator.objects.submit_completion(
            user=user,
            course_key=self.course_key,
            block_key=self.course_key.make_usage_key(block_type='course', block_id='course'),
            aggregation_name='course',
            earned=earned,
            possible=possible,
            last_modified=timezone.now()
        )

