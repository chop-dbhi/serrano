import json
from django.test import TestCase
from avocado.conf import OPTIONAL_DEPS
from serrano.resources import API_VERSION


class ExporterResourceTestCase(TestCase):
    def test_get(self):
        response = self.client.get('/api/data/export/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

        expectedResponse = {
            'title': 'Serrano Exporter Endpoints',
            'version': API_VERSION,
            '_links': {
                'self': {'href': 'http://testserver/api/data/export/'},
                'json': {
                    'href': 'http://testserver/api/data/export/json/',
                    'description': 'JavaScript Object Notation (JSON)',
                    'title': 'JSON'
                },
                'r': {
                    'href': 'http://testserver/api/data/export/r/',
                    'description': 'R Programming Language',
                    'title': 'R'
                },
                'sas': {
                    'href': 'http://testserver/api/data/export/sas/',
                    'description': 'Statistical Analysis System (SAS)',
                    'title': 'SAS'
                },
                'csv': {
                    'href': 'http://testserver/api/data/export/csv/',
                    'description': 'Comma-Separated Values (CSV)',
                    'title': 'CSV'
                }
            },
        }

        if OPTIONAL_DEPS['openpyxl']:
            expectedResponse['_links']['excel'] = {
                'href': 'http://testserver/api/data/export/excel/',
                'description': 'Microsoft Excel 2007 Format',
                'title': 'Excel'
            }

        self.assertEqual(json.loads(response.content), expectedResponse)
