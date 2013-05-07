from django.test import TestCase
from django.http import HttpRequest
from django.contrib.sessions.backends.file import SessionStore
from django.contrib.auth.models import User
from serrano.forms import ContextForm, ViewForm


class ContextFormTestCase(TestCase):
    def setUp(self):
        self.request = HttpRequest()
        self.request.session = SessionStore()
        self.request.session.save()

    def test_session(self):
        form = ContextForm(self.request, {})
        self.assertTrue(form.is_valid())
        self.assertFalse(form.count_needs_update)
        instance = form.save()
        self.assertEqual(instance.user, None)
        self.assertEqual(instance.session_key, self.request.session.session_key)
        self.assertEqual(instance.count, None)

    def test_user(self):
        user = User.objects.create_user(username='test', password='test')
        self.request.user = user

        form = ContextForm(self.request, {})
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(instance.user, user)
        self.assertEqual(instance.session_key, None)


class ViewFormTestCase(TestCase):
    def setUp(self):
        self.request = HttpRequest()
        self.request.session = SessionStore()
        self.request.session.save()

    def test_session(self):
        form = ViewForm(self.request, {})
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(form.instance.user, None)
        self.assertEqual(form.instance.session_key, self.request.session.session_key)

    def test_user(self):
        user = User.objects.create_user(username='test', password='test')
        self.request.user = user

        form = ViewForm(self.request, {})
        self.assertTrue(form.is_valid())
        self.assertFalse(form.count_needs_update)
        instance = form.save()
        self.assertEqual(instance.user, user)
        self.assertEqual(instance.session_key, None)
        self.assertEqual(instance.count, None)
