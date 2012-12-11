from django.test import TestCase
from django.http import HttpRequest
from django.contrib.sessions.backends.file import SessionStore
from django.contrib.auth.models import User
from django.core import management
from serrano.forms import DataContextForm, DataViewForm


class DataContextFormTestCase(TestCase):
    def setUp(self):
        # Mock request object
        self.request = HttpRequest()
        self.request.session = SessionStore()
        self.request.session.save()

    def test(self):
        form = DataContextForm(self.request)
        is_valid = form.is_valid()
        print form.errors
        print form.non_field_errors()
        self.assertTrue(is_valid)
        cleaned_data = form.cleaned_data
        self.assertEqual(cleaned_data['user'], None)
        self.assertEqual(cleaned_data['session_key'], self.request.session.session_key)



class DataViewFormTestCase(TestCase):
    def test(self):
        pass
