import json
from django.test import TestCase
from django.core import management
from django.contrib.auth.models import User
from django.test.utils import override_settings
from avocado.models import DataField


class BaseTestCase(TestCase):
    fixtures = ['resources.json']

    def setUp(self):
        management.call_command('avocado', 'init', 'resources', quiet=True)
        # Only publish some of them..
        DataField.objects.filter(model_name='title').update(published=True)
        self.user = User.objects.create_user(username='root',
            password='password')
        self.user.is_superuser = True
        self.user.save()


class RootResourceTestCase(TestCase):
    def test_get(self):
        response = self.client.get('/api/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(json.loads(response.content), {
            'title': 'Serrano Hypermedia API',
            '_links': {
                'exporter': {'href': '/api/data/export/', 'rel': 'data'},
                'views': {'href': '/api/views/', 'rel': 'dataviews'},
                'contexts': {'href': '/api/contexts/', 'rel': 'datacontexts'},
                'fields': {'href': '/api/fields/', 'rel': 'datafields'},
                'self': {'href': '/api/', 'rel': 'self'},
                'concepts': {'href': '/api/concepts/', 'rel': 'dataconcepts'},
                'preview': {'href': '/api/data/preview/', 'rel': 'data'},
            },
        })

    @override_settings(SERRANO_AUTH_REQUIRED=True)
    def test_post(self):
        User.objects.create_user(username='root', password='password')
        response = self.client.post('/api/',
            content_type='application/json',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.content, 'Invalid credentials')

        response = self.client.post('/api/',
            json.dumps({'username': 'root', 'password': 'password'}),
            content_type='application/json',
            HTTP_ACCEPT='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue('token' in json.loads(response.content))


class DataFieldResourceTestCase(BaseTestCase):
    def test_get_all(self):
        response = self.client.get('/api/fields/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 3)

    def test_get_one(self):
        # Not allowed to see
        response = self.client.get('/api/fields/1/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 404)

        response = self.client.get('/api/fields/2/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content))

    def test_get_privileged(self):
        # Superuser sees everything
        self.client.login(username='root', password='password')

        response = self.client.get('/api/fields/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 11)

        response = self.client.get('/api/fields/1/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content))

    def test_values(self):
        # title.name
        response = self.client.get('/api/fields/2/values/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content))

        # Random values
        response = self.client.get('/api/fields/2/values/?random=3',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content))

        # Query values
        response = self.client.get('/api/fields/2/values/?query=t',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 7)

    def test_stats(self):
        # title.name
        response = self.client.get('/api/fields/2/stats/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content))

        # title.salary
        response = self.client.get('/api/fields/3/stats/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content))

    def test_dist(self):
        # title.salary
        response = self.client.get('/api/fields/3/dist/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {
            u'size': 5,
            u'clustered': False,
            u'outliers': [],
            u'data': [{
                u'count': 3,
                u'values': [15000]
            }, {
                u'count': 1,
                u'values': [10000]
            }, {
                u'count': 1,
                u'values': [20000]
            }, {
                u'count': 1,
                u'values': [100000]
            }, {
                u'count': 1,
                u'values': [200000]
            }],
        })


class DataContextResource(BaseTestCase):
    def test_get_all(self):
        response = self.client.get('/api/contexts/',
            HTTP_ACCEPT='application/json')
        self.assertFalse(json.loads(response.content))
