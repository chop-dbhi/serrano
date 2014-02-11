import json
import time
from django.contrib.auth.models import User
from django.core import management
from django.test import TestCase
from django.test.utils import override_settings
from restlib2.http import codes
from avocado.history.models import Revision
from avocado.models import DataField, DataView
from serrano.resources import API_VERSION
from serrano.models import ApiToken


class BaseTestCase(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        management.call_command('avocado', 'init', 'tests', quiet=True, publish=False, concepts=False)
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
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(json.loads(response.content), {
            'title': 'Serrano Hypermedia API',
            'version': API_VERSION,
            '_links': {
                'exporter': {'href': 'http://testserver/api/data/export/'},
                'views': {'href': 'http://testserver/api/views/'},
                'contexts': {'href': 'http://testserver/api/contexts/'},
                'queries': {'href': 'http://testserver/api/queries/'},
                'public_queries': {'href': 'http://testserver/api/queries/public/'},
                'fields': {'href': 'http://testserver/api/fields/'},
                'categories': {'href': 'http://testserver/api/categories/'},
                'self': {'href': 'http://testserver/api/'},
                'concepts': {'href': 'http://testserver/api/concepts/'},
                'preview': {'href': 'http://testserver/api/data/preview/'},
                'sets': {'href': 'http://testserver/api/sets/'},
                'ping': {'href': 'http://testserver/api/ping/'},
            },
        })

    @override_settings(SERRANO_AUTH_REQUIRED=True)
    def test_post(self):
        User.objects.create_user(username='root', password='password')
        response = self.client.post('/api/',
            content_type='application/json',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.unauthorized)
        self.assertEqual(response.content, 'Invalid credentials')

        response = self.client.post('/api/',
            json.dumps({'username': 'root', 'password': 'password'}),
            content_type='application/json',
            HTTP_ACCEPT='application/json')

        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue('token' in json.loads(response.content))

        # Confirm that passing an invalid username/password returns a status
        # code of codes.unauthorized -- unauthorized.
        response = self.client.post('/api/',
            json.dumps({'username': 'root', 'password': 'NOT_THE_PASSWORD'}),
            content_type='application/json')

        self.assertEqual(response.status_code, codes.unauthorized)

    @override_settings(SERRANO_AUTH_REQUIRED=True)
    def test_api_token_access(self):
        response = self.client.get('/api/',
                                   content_type='application/json',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.unauthorized)

        # Create user token
        user = User.objects.create_user(username='root', password='password')
        api_token = ApiToken.objects.create(user=user)
        self.assertTrue(api_token.token)

        response = self.client.get('/api/',
                                   data={'token': api_token.token},
                                   content_type='application/json',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)


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
            self.assertEqual(response.status_code, codes.ok)

        # Wait a little while but stay in the interval
        time.sleep(3)

        # These 20 requests should be still be OK
        for _ in range(20):
            response = self.client.get('/api/fields/2/',
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, codes.ok)

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
            self.assertEqual(response.status_code, codes.ok)


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
        self.assertEqual(response.status_code, codes.ok)

        # Be certain we are clear of the current interval
        time.sleep(5)

        # These 10 requests should be OK
        for _ in range(10):
            response = self.client.get('/api/fields/2/',
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, codes.ok)

        # Wait a little while but stay in the interval
        time.sleep(1)

        # These 10 requests should be still be OK
        for _ in range(10):
            response = self.client.get('/api/fields/2/',
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, codes.ok)

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
            self.assertEqual(response.status_code, codes.ok)


class RevisionResourceTestCase(AuthenticatedBaseTestCase):
    def test_no_object_model(self):
        # This will trigger a revision to be created
        view = DataView(user=self.user)
        view.save()

        # Make sure we have a revision for this user
        self.assertEqual(Revision.objects.filter(user=self.user).count(), 1)

        response = self.client.get('/api/test/no_model/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 0)

    def test_custom_template(self):
        view = DataView(user=self.user)
        view.save()

        response = self.client.get('/api/test/template/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
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
        self.assertEqual(response.status_code, codes.not_found)

        url = '/api/test/{0}/revisions/'.format(view.id)
        response = self.client.get(url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)


class PingResourceTestCase(AuthenticatedBaseTestCase):
    @override_settings(SERRANO_AUTH_REQUIRED=True)
    def test(self):
        response = self.client.get('/api/ping/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(json.loads(response.content)['status'], 'ok')

        # emulate session timeout..
        self.client.logout()

        response = self.client.get('/api/ping/',
                                   HTTP_ACCEPT='application/json',
                                   HTTP_REFERER='http://testserver/query/')

        data = json.loads(response.content)
        self.assertEqual(data['status'], 'timeout')
        self.assertEqual(data['location'],
                         'http://testserver/accounts/login/?next=/query/')

    @override_settings(SERRANO_AUTH_REQUIRED=True, LOGIN_REDIRECT_URL='/')
    def test_nonsafe_referer(self):
        self.client.logout()

        response = self.client.get('/api/ping/',
                                   HTTP_ACCEPT='application/json',
                                   HTTP_REFERER='http://example.com/spam/')

        data = json.loads(response.content)
        self.assertEqual(data['status'], 'timeout')
        self.assertEqual(data['location'],
                         'http://testserver/accounts/login/?next=/')
