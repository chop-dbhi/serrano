import time
from django.http import HttpResponseRedirect
from restlib2.http import codes

from avocado.models import DataQuery
from avocado.async import utils
from .base import JobTestCaseMixin
from ..base import AuthenticatedBaseTestCase


class AsyncQueryResultsResourceTestCase(AuthenticatedBaseTestCase,
                                        JobTestCaseMixin):
    def setUp(self):
        super(AsyncQueryResultsResourceTestCase, self).setUp()
        utils.cancel_all_jobs()
        self.query = DataQuery(user=self.user)
        self.query.save()

    def test_get_bad_url(self):
        # This ID should not exist.
        response = self.client.get('api/async/queries/999/results/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)

        # We haven't created any DataQuery objects with session=True so there
        # should be no session query to get results for.
        response = self.client.get('/api/async/queries/session/results/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)

    def test_get(self):
        job = self.request_and_assert_job(
            '/api/async/queries/{0}/results/'.format(self.query.id))

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
        self.assert_job_result_equal(job, [])

    def test_get_session(self):
        # Make sure we have a session query.
        query = DataQuery(user=self.user, name='Query', session=True)
        query.save()

        # All results for session query.
        response = self.client.get('/api/async/queries/session/results/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(
            response.status_code, HttpResponseRedirect.status_code)
        normal_job_id = response['Location'].split('/')[-2]

        # Single page of results for session query.
        response = self.client.get('/api/async/queries/session/results/3/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(
            response.status_code, HttpResponseRedirect.status_code)
        paged_job_id = response['Location'].split('/')[-2]

        # Page range of results for session query.
        response = self.client.get('/api/async/queries/session/results/1...5/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(
            response.status_code, HttpResponseRedirect.status_code)
        range_job_id = response['Location'].split('/')[-2]

        # The three requests above should have triggered 3 queued jobs.
        self.assertEqual(utils.get_job_count(), 3)
        for job_id in [normal_job_id, paged_job_id, range_job_id]:
            self.assert_job_status_equal(
                utils.get_job(job_id), 'queued')

        # Sleeping a couple seconds should leave plenty of time for the worker
        # to do its thing and finish up the three jobs from above.
        utils.run_jobs()
        time.sleep(3)

        # The three previous requests should now all be completed and their
        # items should match what we expect.
        for job_id in [normal_job_id, paged_job_id, range_job_id]:
            self.assert_job_status_equal(
                utils.get_job(job_id), 'finished')
            self.assert_job_result_equal(utils.get_job(job_id), [])

    def test_page(self):
        job = self.request_and_assert_job(
            '/api/async/queries/{0}/results/3/'.format(self.query.id))
        utils.run_jobs()
        self.assert_job_status_equal(job, 'finished')
        self.assert_job_result_equal(job, [])

    def test_page_range(self):
        job = self.request_and_assert_job(
            '/api/async/queries/{0}/results/3...50/'.format(self.query.id))
        utils.run_jobs()
        self.assert_job_status_equal(job, 'finished')
        self.assert_job_result_equal(job, [])
