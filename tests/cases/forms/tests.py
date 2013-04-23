from django.test import TestCase
from django.http import HttpRequest
from django.contrib.sessions.backends.file import SessionStore
from django.contrib.auth.models import User
from django.core import management
from serrano.forms import ContextForm, ViewForm


class ContextFormTestCase(TestCase):
    def setUp(self):
        # Mock request object
        self.request = HttpRequest()
        self.request.session = SessionStore()
        self.request.session.save()

    def test(self):
        form = ContextForm(self.request, {})
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(form.cleaned_data.get('user'), None)
        self.assertEqual(form.instance.session_key, self.request.session.session_key)



class ViewFormTestCase(TestCase):
    def test(self):
        pass
