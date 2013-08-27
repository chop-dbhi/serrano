import json
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from avocado import history
from avocado.history.models import Revision
from avocado.models import DataView
from .base import AuthenticatedBaseTestCase


class ViewResourceTestCase(AuthenticatedBaseTestCase):
    def test_get_all(self):
        response = self.client.get('/api/views/',
            HTTP_ACCEPT='application/json')
        self.assertFalse(json.loads(response.content))

    def test_get_all_default(self):
        view = DataView(template=True, default=True, json={})
        view.save()
        response = self.client.get('/api/views/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 1)

    def test_get(self):
        view = DataView(user=self.user)
        view.save()
        response = self.client.get('/api/views/1/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content)
        self.assertLess(view.accessed,
                DataView.objects.get(pk=view.pk).accessed)


class ViewsRevisionsResourceTestCase(AuthenticatedBaseTestCase):
    def test_get(self):
        view = DataView(user=self.user)
        view.save()

        response = self.client.get('/api/views/revisions/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 1)

    def test_user(self):
        view = DataView(user=self.user)
        view.save()

        user2 = User.objects.create_user(username='FAKE', password='ALSO_FAKE')
        view2 = DataView(user=user2)
        view2.save()

        self.assertEqual(Revision.objects.filter(
            content_type=ContentType.objects.get_for_model(DataView)).count(), 2)

        response = self.client.get('/api/views/revisions/',
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

        response = self.client.get('/api/views/revisions/',
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

        response = self.client.get('/api/views/revisions/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 0)
