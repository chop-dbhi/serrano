import json
from django.test import TestCase


class PreviewResourceTestCase(TestCase):
    def test_get(self):
        response = self.client.get('/api/data/preview/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(json.loads(response.content), {
            '_links': {
                'self': {
                    'href': 'http://testserver/api/data/preview/?limit=20&page=1',
                },
                'base': {
                    'href': 'http://testserver/api/data/preview/',
                }
            },
            'keys': [],
            'object_count': 0,
            'object_name': 'employee',
            'object_name_plural': 'employees',
            'objects': [],
            'page_num': 1,
            'num_pages': 1,
            'limit': 20,
        })
