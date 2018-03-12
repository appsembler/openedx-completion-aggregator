"""
Testing the functionality of asynchronous tasks
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import itertools
from datetime import timedelta

import six
from mock import MagicMock
from opaque_keys.edx.keys import CourseKey
from xblock.completable import XBlockCompletionMode
from xblock.core import XBlock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.timezone import now

from completion.models import BlockCompletion
from completion_aggregator.models import Aggregator
from completion_aggregator.tasks import AggregationUpdater


class StubAggregationUpdater(AggregationUpdater):
    """
    An AggregationUpdater with connections to edx-platform and modulestore
    replaced with local elements.
    """
    def init_course_block_key(self, modulestore, course_key):
        """
        Create a root usage key for the course.

        For the purposes of testing, we're just going by convention.
        """
        return course_key.make_usage_key('course', 'course')

    def init_course_blocks(self, user, course_block_key):
        """
        Not actually used in this implmentation.

        Overridden here to prevent the default behavior, which relies on
        modulestore.
        """
        pass

    def _get_block_completions(self):
        """
        Return all completions for the current course.
        """
        return BlockCompletion.objects.filter(user=self.user, course_key=self.course_key)

    def _get_children(self, block_key):
        """
        Return children for the given block.

        For the purpose of the tests, we will use the following course
        structure:

                        course
                          |
                +--+---+--^-+----+----+
               /   |   |    |    |     \
            html html html html other hidden
                                /   \
                              html hidden

        where `course` and `other` are a completion_mode of AGGREGATOR (but
        only `course` is registered to store aggregations), `html` is
        COMPLETABLE, and `hidden` is EXCLUDED.
        """
        if block_key.block_type == 'course':
            return list(itertools.chain(
                [self.course_key.make_usage_key('html', 'html{}'.format(i)) for i in six.moves.range(4)],
                [self.course_key.make_usage_key('other', 'other')],
                [self.course_key.make_usage_key('hidden', 'hidden0')]
            ))
        elif block_key.block_type == 'other':
            return [
                self.course_key.make_usage_key('html', 'html4'),
                self.course_key.make_usage_key('hidden', 'hidden1')
            ]
        return []


class CourseBlock(XBlock):
    """
    A registered aggregator block.
    """
    completion_mode = XBlockCompletionMode.AGGREGATOR


class HTMLBlock(XBlock):
    """
    A completable block.
    """
    completion_mode = XBlockCompletionMode.COMPLETABLE


class HiddenBlock(XBlock):
    """
    An excluded block.
    """
    completion_mode = XBlockCompletionMode.EXCLUDED


class OtherAggBlock(XBlock):
    """
    An unregistered aggregator block.
    """
    completion_mode = XBlockCompletionMode.AGGREGATOR


class AggregationUpdaterTestCase(TestCase):
    """
    Test the AggregationUpdater.

    It should create Aggregator records for new completion objects.
    """
    def setUp(self):
        self.agg_modified = now() - timedelta(days=1)
        user = get_user_model().objects.create()
        self.course_key = CourseKey.from_string('course-v1:edx+course+test')
        self.agg, _ = Aggregator.objects.submit_completion(
            user=user,
            course_key=self.course_key,
            block_key=self.course_key.make_usage_key('course', 'course'),
            aggregation_name='course',
            earned=0.0,
            possible=0.0,
            last_modified=self.agg_modified,
        )
        BlockCompletion.objects.create(
            user=user,
            course_key=self.course_key,
            block_key=self.course_key.make_usage_key('html', 'html4'),
            completion=1.0,
            modified=now(),
        )
        self.updater = StubAggregationUpdater(user, self.course_key, MagicMock())

    @XBlock.register_temp_plugin(CourseBlock, 'course')
    @XBlock.register_temp_plugin(HTMLBlock, 'html')
    @XBlock.register_temp_plugin(HiddenBlock, 'hidden')
    @XBlock.register_temp_plugin(OtherAggBlock, 'other')
    def test_aggregation_update(self):
        self.updater.update()
        self.agg.refresh_from_db()
        assert self.agg.last_modified > self.agg_modified
        assert self.agg.earned == 1.0
        assert self.agg.possible == 5.0

    @XBlock.register_temp_plugin(CourseBlock, 'course')
    @XBlock.register_temp_plugin(HTMLBlock, 'html')
    @XBlock.register_temp_plugin(HiddenBlock, 'hidden')
    @XBlock.register_temp_plugin(OtherAggBlock, 'other')
    def test_unregistered_not_recorded(self):
        self.updater.update()
        assert not any(agg.block_key.block_type == 'other' for agg in Aggregator.objects.all())

    @XBlock.register_temp_plugin(CourseBlock, 'course')
    @XBlock.register_temp_plugin(HTMLBlock, 'html')
    @XBlock.register_temp_plugin(HiddenBlock, 'hidden')
    @XBlock.register_temp_plugin(OtherAggBlock, 'other')
    def test_with_no_initial_aggregator(self):
        self.agg.delete()
        self.updater.update()
        aggs = Aggregator.objects.filter(course_key=self.course_key)
        assert len(aggs) == 1
        agg = aggs[0]
        assert agg.course_key == self.course_key
        assert agg.aggregation_name == 'course'
        assert agg.earned == 1.0
        assert agg.possible == 5.0
