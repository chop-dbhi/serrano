import json
import time
from django.contrib.auth.models import User
from django.core import management
from django.test import TestCase
from django.test.utils import override_settings
from avocado.history.models import Revision
from avocado.models import DataField, DataView
from restlib2.http import codes
from serrano.resources import API_VERSION


class BaseTestCase(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        management.call_command('avocado', 'init', 'tests', quiet=True)
        # Only publish some of them..
        DataField.objects.filter(model_name__in=['project', 'title']).update(published=True)
        self.user = User.objects.create_user(username='root',
            password='password')
        self.user.is_superuser = True
        self.user.save()


class AuthenticatedBaseTestCase(BaseTestCase):
    def setUp(self):
        super(AuthenticatedBaseTestCase, self).setUp()

        self.user = User.objects.create_user(username='test', password='test')
        self.client.login(username='test', password='test')


class RootResourceTestCase(TestCase):
    def test_get(self):
        response = self.client.get('/api/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(json.loads(response.content), {
            'title': 'Serrano Hypermedia API',
            'version': API_VERSION,
            '_links': {
                'exporter': {'href': 'http://testserver/api/data/export/'},
                'views': {'href': 'http://testserver/api/views/'},
                'contexts': {'href': 'http://testserver/api/contexts/'},
                'queries': {'href': 'http://testserver/api/queries/'},
                'fields': {'href': 'http://testserver/api/fields/'},
                'self': {'href': 'http://testserver/api/'},
                'concepts': {'href': 'http://testserver/api/concepts/'},
                'preview': {'href': 'http://testserver/api/data/preview/'},
                'shared_queries': {'href': 'http://testserver/api/queries/shared/'},
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


@override_settings(SERRANO_RATE_LIMIT_COUNT=None)
class ThrottledResourceTestCase(BaseTestCase):
    def test_too_many_auth_requests(self):
        self.client.login(username='root', password='password')

        # Be certain we are clear of the current interval
        time.sleep(7)

        # These 20 requests should be OK
        for _ in range(20):
            response = self.client.get('/api/fields/2/',
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 200)

        # Wait a little while but stay in the interval
        time.sleep(3)

        # These 20 requests should be still be OK
        for _ in range(20):
            response = self.client.get('/api/fields/2/',
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 200)

        # These 10 requests should fail as we've exceeded the limit
        for _ in range(10):
            response = self.client.get('/api/fields/2/',
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, codes.too_many_requests)

        # Wait out the interval
        time.sleep(6)

        # These 5 requests should be OK
        for _ in range(5):
            response = self.client.get('/api/fields/2/',
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 200)


    def test_too_many_requests(self):
        # Force these the requests to be unauthenitcated
        self.user = None

        # We execute a request before the actual test in order to initialize
        # the session so that we have valid session keys on subsequent
        # requests.
        # TODO: Can the session be initialized somehow without sending
        # a request via the client?
        response = self.client.get('/api/fields/2/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)

        # Be certain we are clear of the current interval
        time.sleep(5)

        # These 10 requests should be OK
        for _ in range(10):
            response = self.client.get('/api/fields/2/',
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 200)

        # Wait a little while but stay in the interval
        time.sleep(1)

        # These 10 requests should be still be OK
        for _ in range(10):
            response = self.client.get('/api/fields/2/',
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 200)

        # These 10 requests should fail as we've exceeded the limit
        for _ in range(10):
            response = self.client.get('/api/fields/2/',
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, codes.too_many_requests)

        # Wait out the interval
        time.sleep(4)

        # These 5 requests should be OK
        for _ in range(5):
            response = self.client.get('/api/fields/2/',
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 200)


class RevisionResourceTestCase(AuthenticatedBaseTestCase):
    def test_no_object_model(self):
        # This will trigger a revision to be created
        view = DataView(user=self.user)
        view.save()

        # Make sure we have a revision for this user
        self.assertEqual(Revision.objects.filter(user=self.user).count(), 1)

        response = self.client.get('/api/test/no_model/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 0)

    def test_custom_template(self):
        view = DataView(user=self.user)
        view.save()

        response = self.client.get('/api/test/template/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 1)

        revision = json.loads(response.content)[0]
        self.assertEqual(revision['id'], 1)
        self.assertEqual(revision['object_id'], 1)
        self.assertTrue('_links' in revision)
        self.assertFalse('content_type' in revision)


class ObjectRevisionResourceTestCase(AuthenticatedBaseTestCase):
    def test_bad_urls(self):
        view = DataView(user=self.user)
        view.save()

        target_revision_id = Revision.objects.all().count()

        url = '/api/test/revisions/{0}/'.format(target_revision_id)
        response = self.client.get(url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 404)

        url = '/api/test/{0}/revisions/'.format(view.id)
        response = self.client.get(url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 404)
