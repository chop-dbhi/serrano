import json
import time

from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.test import TestCase
from restlib2.http import codes

from avocado.async import utils
from .base import JobTestCaseMixin
from ..base import TransactionBaseTestCase


class AsyncPreviewResourceProcessorTestCase(
        TransactionBaseTestCase, JobTestCaseMixin):
    def setUp(self):
        # Clear all jobs before each test case just in case any lingering jobs
        # remain.
        utils.cancel_all_jobs()

        super(AsyncPreviewResourceProcessorTestCase, self).setUp()

    def test_no_processor(self):
        response = self.client.get('/api/async/preview/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(
            response.status_code, HttpResponseRedirect.status_code)
        normal_job_id = response['Location'].split('/')[-2]

        # Add an async request with a valid processor.
        response = self.client.get('/api/async/preview/?processor=manager',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(
            response.status_code, HttpResponseRedirect.status_code)
        valid_job_id = response['Location'].split('/')[-2]

        # The Parametizer cleaning process should set this to the default
        # value if the processor is not in the list of choices which, in our
        # case, is the list of available query processors so we should just
        # end up with the default processor.
        response = self.client.get('/api/async/preview/?processor=INVALID',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(
            response.status_code, HttpResponseRedirect.status_code)
        invalid_job_id = response['Location'].split('/')[-2]

        # The three requests above should have triggered 3 queued jobs.
        self.assertEqual(utils.get_job_count(), 3)
        for job_id in [normal_job_id, valid_job_id, invalid_job_id]:
            self.assert_job_status_equal(
                utils.get_job(job_id), 'queued')

        # Sleeping a couple seconds should leave plenty of time for the worker
        # to do its thing and finish up the three jobs from above.
        utils.run_jobs()
        time.sleep(3)

        # The three previous requests should now all be completed and their
        # items should match what we expect.
        for job_id in [normal_job_id, invalid_job_id, valid_job_id]:
            self.assert_job_status_equal(
                utils.get_job(job_id), 'finished')

        # When no processor is specified, all rows should be in the job result.
        response = self.client.get(
            '/api/jobs/{0}/result/'.format(normal_job_id),
            HTTP_ACCEPT='application/json')
        content = json.loads(response.content)
        self.assertEqual(len(content['items']), 6)

        # When the manager processor is used, only a single row should be in
        # the result set.
        response = self.client.get(
            '/api/jobs/{0}/result/'.format(valid_job_id),
            HTTP_ACCEPT='application/json')
        content = json.loads(response.content)
        self.assertEqual(len(content['items']), 1)

        # When an invalid processor is specified, the default processor should
        # be used. As we see above, the default processor should return all
        # the rows.
        response = self.client.get(
            '/api/jobs/{0}/result/'.format(invalid_job_id),
            HTTP_ACCEPT='application/json')
        content = json.loads(response.content)
        self.assertEqual(len(content['items']), 6)


class AsyncPreviewResourceTestCase(TestCase, JobTestCaseMixin):
    def setUp(self):
        # Clear all jobs before each test case just in case any lingering jobs
        # remain.
        utils.cancel_all_jobs()

    def test_get(self):
        job = self.request_and_assert_job('/api/async/preview/')

        # The job endpoint should tell us the job is queued since we don't
        # have any workers running yet.
        self.assert_job_status_equal(job, 'queued')

        # Since the job is queued and not yet processed, the result endpoint
        # should return a 404.
        response = self.client.get('/api/jobs/{0}/result/'.format(job.id),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)

        # Let's start a worker, this should process the job which should cause
        # it to go to complete status and make its result available.
        utils.run_jobs()

        self.assert_job_status_equal(job, 'finished')
        self.assert_job_result_equal(job, {
            'item_name': 'employee',
            'items': [],
            'keys': [],
            'limit': None,
            'item_name_plural': 'employees',
        })

    def test_get_page(self):
        job = self.request_and_assert_job('/api/async/preview/7/')
        utils.run_jobs()
        self.assert_job_status_equal(job, 'finished')
        self.assert_job_result_equal(job, {
            'item_name': 'employee',
            'items': [],
            'keys': [],
            'item_name_plural': 'employees',
            'limit': 20,
        })

    def test_get_page_range_equal(self):
        job = self.request_and_assert_job('/api/async/preview/3...3/')
        utils.run_jobs()
        self.assert_job_status_equal(job, 'finished')

        result = {
            'item_name': 'employee',
            'items': [],
            'keys': [],
            'item_name_plural': 'employees',
            'limit': 20,
        }
        links = (
            '<http://testserver/api/async/preview/?limit=20&page=2>; rel="prev", '   # noqa
            '<http://testserver/api/async/preview/?limit=20&page=3>; rel="self", '   # noqa
            '<http://testserver/api/async/preview/>; rel="base", '
            '<http://testserver/api/async/preview/?limit=20&page=4>; rel="next", '    # noqa
            '<http://testserver/api/async/preview/?limit=20&page=1>; rel="first"'   # noqa
        )
        self.assert_job_result_equal(job, result, links)

    def test_get_page_range(self):
        job = self.request_and_assert_job('/api/async/preview/1...5/')
        utils.run_jobs()
        self.assert_job_status_equal(job, 'finished')
        self.assert_job_result_equal(job, {
            'item_name': 'employee',
            'items': [],
            'keys': [],
            'item_name_plural': 'employees',
            'limit': 100,
        })

    def test_get_limit(self):
        job = self.request_and_assert_job('/api/async/preview/1/?limit=1000')
        utils.run_jobs()
        self.assert_job_status_equal(job, 'finished')
        self.assert_job_result_equal(job, {
            'item_name': 'employee',
            'items': [],
            'keys': [],
            'item_name_plural': 'employees',
            'limit': 1000,
        })

    def test_get_with_user(self):
        self.user = User.objects.create_user(username='test', password='test')
        self.client.login(username='test', password='test')

        job = self.request_and_assert_job('/api/async/preview/')
        utils.run_jobs()
        self.assert_job_status_equal(job, 'finished')

        result = {
            'item_name': 'employee',
            'items': [],
            'keys': [],
            'limit': None,
            'item_name_plural': 'employees',
        }
        links = (
            '<http://testserver/api/async/preview/>; rel="self"'
        )
        self.assert_job_result_equal(job, result, links)
