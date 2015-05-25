import json
import uuid

from django.test import TestCase
from django.http import HttpResponseRedirect
from restlib2.http import codes

from avocado.async import utils


class JobTestCaseMixin(object):
    def request_and_assert_job(self, url, accept='application/json'):
        initial_count = utils.get_job_count()

        # We should be told to look for our answers elsewhere. Specifically,
        # we should get a redirect with the location being the resource for
        # the job created by the request.
        response = self.client.get(url, HTTP_ACCEPT=accept)
        self.assertEqual(
            response.status_code, HttpResponseRedirect.status_code)

        # Verify that the job is scheduled and that the URL we received
        # matches the job.
        self.assertEqual(utils.get_job_count(), initial_count + 1)
        job = utils.get_jobs()[initial_count]
        location = response['Location']
        self.assertEqual(
            location, 'http://testserver/api/jobs/{0}/'.format(job.id))

        return job

    def assert_job_status_equal(self, job, expected_status):
        response = self.client.get('/api/jobs/{0}/'.format(job.id),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        content = json.loads(response.content)
        self.assertEqual(content['status'], expected_status)

    def assert_job_result_equal(self, job, expected_result,
                                expected_links=None):
        response = self.client.get('/api/jobs/{0}/result/'.format(job.id),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(json.loads(response.content), expected_result)

        if expected_links:
            self.assert_links_equal(response['Link'], expected_links)

    def assert_links_equal(self, link_str, expected_link_str):
        # Cannot use set comprehension here because it is not supported
        # in Python 2.6. Set comprehensions were backported from 3.1 to 2.7.
        links = set(link.strip() for link in link_str.split(','))
        expected_links = set(
            link.strip() for link in expected_link_str.split(','))
        self.assertEqual(links, set(expected_links))


class JobTestCase(TestCase, JobTestCaseMixin):
    def setUp(self):
        # Clear all scheduled jobs before each test just in case any
        # lingering jobs remain.
        utils.cancel_all_jobs()

    def test_delete(self):
        # Make an async request to stage a job. Doesn't really matter which
        # async endpoint we use so preview is fine.
        job = self.request_and_assert_job('/api/async/preview/')

        # The job endpoint should tell us the job is queued since we don't
        # have any workers running yet.
        self.assert_job_status_equal(job, 'queued')

        response = self.client.delete('/api/jobs/{0}/'.format(job.id),
                                      HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.no_content)

        # Make a delete request to the job endpoint. This should remove the
        # the job from the queue.
        response = self.client.get('/api/jobs/{0}/'.format(job.id),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)

    def test_delete_invalid_job(self):
        # Trying to delete a job that is not in the queue should result in
        # a 404 not found response.
        fake_job_id = str(uuid.uuid4())
        response = self.client.get('/api/jobs/{0}/'.format(fake_job_id),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)
