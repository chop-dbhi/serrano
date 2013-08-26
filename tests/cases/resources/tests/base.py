import json
import time
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.backends.db import SessionStore
from django.core import management
from django.test import Client, TestCase
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
class DataResourceTestCase(BaseTestCase):
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


class HistoryResourceTestCase(BaseTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test', password='test')
        self.client.login(username='test', password='test')

    def test_user(self):
        view = DataView(user=self.user)
        view.save()

        user2 = User.objects.create_user(username='FAKE', password='ALSO_FAKE')
        view2 = DataView(user=user2)
        view2.save()

        self.assertEqual(Revision.objects.filter(
            content_type=ContentType.objects.get_for_model(DataView)).count(), 2)

        response = self.client.get('/api/test/views/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 1)

    def test_session(self):
        # This session mumbo-jumbo is from:
        #       https://code.djangoproject.com/ticket/10899
        self.client = Client()
        from django.conf import settings
        from django.utils.importlib import import_module
        engine = import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore()
        store.save()  # we need to make load() work, or the cookie is worthless
        session_key = store.session_key
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session_key

        view = DataView(session_key=self.client.session.session_key)
        view.save()

        view2 = DataView(session_key='XYZ')
        view2.save()

        self.assertEqual(Revision.objects.filter(
            content_type=ContentType.objects.get_for_model(DataView)).count(), 2)

        response = self.client.get('/api/test/views/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 1)

    def test_no_identifier(self):
        view = DataView()
        view.save()

        # Make sure the revision was created but has nothing useful in
        # either of the "owner" properties.
        self.assertEqual(Revision.objects.filter(
            content_type=ContentType.objects.get_for_model(DataView),
            user=None, session_key=None).count(), 1)

        # We want this request to come from an anonymous user
        self.client.logout()

        response = self.client.get('/api/test/views/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 0)

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
