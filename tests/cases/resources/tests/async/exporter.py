import time
from django.http import HttpResponseRedirect
from django.test import TestCase
from restlib2.http import codes

from avocado.async import utils
from .base import JobTestCaseMixin


class AsyncExporterResourceTestCase(TestCase, JobTestCaseMixin):
    def setUp(self):
        super(AsyncExporterResourceTestCase, self).setUp()
        utils.cancel_all_jobs()

    def test_export_all_pages(self):
        response = self.client.get('/api/async/export/csv/')
        self.assertEqual(
            response.status_code, HttpResponseRedirect.status_code)
        job_id = response['Location'].split('/')[-2]

        utils.run_jobs()
        time.sleep(1)

        response = self.client.get('/api/jobs/{0}/result/'.format(job_id))
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(response.get('Content-Disposition').startswith(
            'attachment; filename="all'))
        self.assertEqual(response.get('Content-Type'), 'text/csv')

    def test_export_one_page(self):
        response = self.client.get('/api/async/export/csv/1/')
        self.assertEqual(
            response.status_code, HttpResponseRedirect.status_code)
        job_id = response['Location'].split('/')[-2]

        utils.run_jobs()
        time.sleep(1)

        response = self.client.get('/api/jobs/{0}/result/'.format(job_id))
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(response.get('Content-Disposition').startswith(
            'attachment; filename="p1'))
        self.assertEqual(response.get('Content-Type'), 'text/csv')

    def test_export_page_range(self):
        response = self.client.get('/api/async/export/csv/1...2/')
        self.assertEqual(
            response.status_code, HttpResponseRedirect.status_code)
        job_id = response['Location'].split('/')[-2]

        utils.run_jobs()
        time.sleep(1)

        response = self.client.get('/api/jobs/{0}/result/'.format(job_id))
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(response.get('Content-Disposition').startswith(
            'attachment; filename="p1-2'))
        self.assertEqual(response.get('Content-Type'), 'text/csv')

    def test_export_equal_page_range(self):
        response = self.client.get('/api/async/export/csv/1...1/')
        self.assertEqual(
            response.status_code, HttpResponseRedirect.status_code)
        job_id = response['Location'].split('/')[-2]

        utils.run_jobs()
        time.sleep(1)

        response = self.client.get('/api/jobs/{0}/result/'.format(job_id))
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(response.get('Content-Disposition').startswith(
            'attachment; filename="p1'))
        self.assertEqual(response.get('Content-Type'), 'text/csv')
