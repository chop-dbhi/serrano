import json
from django.contrib.auth.models import User
from django.test import TestCase
from restlib2.http import codes
from .base import BaseTestCase


class PreviewResourceProcessorTestCase(BaseTestCase):
    def test_no_processor(self):
        response = self.client.get('/api/data/preview/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        content = json.loads(response.content)
        self.assertEqual(content['object_count'], 6)

        # The Parametizer cleaning process should set this to the default
        # value if the processor is not in the list of choices which, in our
        # case, is the list of available query processors so we should just
        # end up with the default processor.
        response = self.client.get('/api/data/preview/?processor=INVALID',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        content = json.loads(response.content)
        self.assertEqual(content['object_count'], 6)

        response = self.client.get('/api/data/preview/?processor=manager',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        content = json.loads(response.content)
        self.assertEqual(content['object_count'], 1)


class PreviewResourceTestCase(TestCase):
    def test_get(self):
        response = self.client.get('/api/data/preview/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(json.loads(response.content), {
            '_links': {
                'self': {
                    'href': 'http://testserver/api/data/preview/?'
                            'limit=20&page=1',
                },
                'base': {
                    'href': 'http://testserver/api/data/preview/',
                }
            },
            'keys': [],
            'count': 0,
            'object_count': 0,
            'object_name': 'employee',
            'object_name_plural': 'employees',
            'objects': [],
            'page_num': 1,
            'num_pages': 1,
            'limit': 20,
        })

    def test_get_with_user(self):
        self.user = User.objects.create_user(username='test', password='test')
        self.client.login(username='test', password='test')

        response = self.client.get('/api/data/preview/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(json.loads(response.content), {
            '_links': {
                'self': {
                    'href': 'http://testserver/api/data/preview/?'
                            'limit=20&page=1',
                },
                'base': {
                    'href': 'http://testserver/api/data/preview/',
                }
            },
            'keys': [],
            'count': 0,
            'object_count': 0,
            'object_name': 'employee',
            'object_name_plural': 'employees',
            'objects': [],
            'page_num': 1,
            'num_pages': 1,
            'limit': 20,
        })
