import logging
import time
from django.contrib.sessions.backends.file import SessionStore
from django.contrib.auth.models import User
from django.core import mail, management
from django.http import HttpRequest
from django.test import TestCase
from django.test.utils import override_settings
from avocado.models import DataConcept, DataConceptField, DataContext, \
    DataField, DataView
from serrano.forms import ContextForm, QueryForm, ViewForm
from ...models import Employee, MockHandler


class BaseTestCase(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        management.call_command('avocado', 'init', 'tests', quiet=True)

        f1 = DataField.objects.get(pk=1)
        f2 = DataField.objects.get(pk=2)

        c1 = DataConcept()
        c1.save()

        DataConceptField(concept=c1, field=f1).save()
        DataConceptField(concept=c1, field=f2).save()

        self.request = HttpRequest()
        self.request.session = SessionStore()
        self.request.session.save()


class ContextFormTestCase(BaseTestCase):
    def test_session(self):
        form = ContextForm(self.request, {})
        self.assertTrue(form.is_valid())
        self.assertFalse(form.count_needs_update)
        instance = form.save()
        self.assertIsNone(instance.user)
        self.assertEqual(instance.session_key,
                         self.request.session.session_key)
        self.assertIsNone(instance.count)

    def test_user(self):
        user = User.objects.create_user(username='test', password='test')
        self.request.user = user

        form = ContextForm(self.request, {})
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(instance.user, user)
        self.assertEqual(instance.session_key, None)

    def test_json(self):
        expected_count = \
            Employee.objects.filter(title__salary__gt=1000).count()

        form = ContextForm(self.request, {'json': {
            'field': 'tests.title.salary', 'operator': 'gt', 'value': '1000'}})
        self.assertTrue(form.is_valid())

        instance = form.save()
        self.assertEqual(instance.count, expected_count)

    def test_force_count(self):
        expected_count = Employee.objects.distinct().count()
        form = ContextForm(self.request, {}, force_count=True)
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(instance.count, expected_count)

    def test_no_commit(self):
        previous_context_count = DataContext.objects.count()

        form = ContextForm(self.request, {})
        instance = form.save(commit=False)

        self.assertIsNone(instance.pk)
        self.assertEqual(previous_context_count, DataContext.objects.count())


class ViewFormTestCase(BaseTestCase):
    def test_session(self):
        form = ViewForm(self.request, {})
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(form.instance.user, None)
        self.assertEqual(form.instance.session_key,
                         self.request.session.session_key)

    def test_user(self):
        user = User.objects.create_user(username='test', password='test')
        self.request.user = user

        form = ViewForm(self.request, {})
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(instance.user, user)
        self.assertEqual(instance.session_key, None)

    def test_json(self):
        previous_view_count = DataView.objects.count()

        form = ViewForm(self.request, {'json': [{'concept': 1}]})
        self.assertTrue(form.is_valid())

        form.save()
        self.assertEqual(previous_view_count + 1, DataView.objects.count())

    def test_no_commit(self):
        previous_view_count = DataView.objects.count()

        form = ViewForm(self.request, {})
        instance = form.save(commit=False)

        self.assertIsNone(instance.pk)
        self.assertEqual(previous_view_count, DataView.objects.count())


class QueryFormTestCase(BaseTestCase):
    def setUp(self):
        super(QueryFormTestCase, self).setUp()

        from serrano import forms
        # Setup a mock handler
        self.logger = logging.getLogger(forms.__name__)
        self.mock_handler = MockHandler()
        self.logger.addHandler(self.mock_handler)

    def test_session(self):
        form = QueryForm(self.request, {})
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(form.instance.user, None)
        self.assertEqual(form.instance.session_key,
                         self.request.session.session_key)

    def test_user(self):
        user = User.objects.create_user(username='test', password='test')
        self.request.user = user

        form = QueryForm(self.request, {})
        self.assertTrue(form.is_valid())
        self.assertFalse(form.count_needs_update_context)
        self.assertFalse(form.count_needs_update_view)
        instance = form.save()
        self.assertEqual(instance.user, user)
        self.assertEqual(instance.session_key, None)

    @override_settings(SERRANO_QUERY_REVERSE_NAME='results')
    def test_with_email(self):
        previous_user_count = User.objects.count()
        previous_mail_count = len(mail.outbox)

        form = QueryForm(self.request, {'usernames_or_emails':
                                        'email1@email.com'})
        instance = form.save()
        self.assertEqual(instance.shared_users.count(), 1)

        # Since save sends email asynchronously, wait for a while for the mail
        # to go through.
        time.sleep(5)

        # Make sure the user was created
        self.assertEqual(previous_user_count + 1, User.objects.count())

        # Make sure the mail was sent
        self.assertEqual(previous_mail_count + 1, len(mail.outbox))

        # Make sure the recipient list is correct
        self.assertSequenceEqual(mail.outbox[0].to, ['email1@email.com'])

    def test_with_user(self):
        user = User.objects.create_user(username='user_1',
                                        email='user_1@email.com')
        user.save()

        form = QueryForm(self.request, {'usernames_or_emails': 'user_1'})
        instance = form.save()
        self.assertEqual(instance.shared_users.count(), 1)

        # Since save sends email asynchronously, wait for a while for the mail
        # to go through.
        time.sleep(5)

        # Make sure the email was sent
        self.assertEqual(len(mail.outbox), 1)

        # Make sure the recipient list is correct
        self.assertSequenceEqual(mail.outbox[0].to, ['user_1@email.com'])

    def test_with_mixed(self):
        user = User.objects.create_user(username='user_1',
                                        email='user_1@email.com')
        user.save()

        previous_user_count = User.objects.count()

        form = QueryForm(self.request, {'usernames_or_emails': 'user_1, \
            valid@email.com, invalid+=email@fake@domain@com, '})
        instance = form.save()
        self.assertEqual(instance.shared_users.count(), 2)

        # Since save sends email asynchronously, wait for a while for the mail
        # to go through.
        time.sleep(5)

        # Make sure the user was created
        self.assertEqual(previous_user_count + 1, User.objects.count())

        # Make sure the mail was sent
        self.assertEqual(len(mail.outbox), 1)

        # Make sure the recipient list is correct
        self.assertSequenceEqual(mail.outbox[0].to, ['user_1@email.com',
                                                     'valid@email.com'])

        # Remove a user from the list
        previous_user_count = User.objects.count()
        form = QueryForm(self.request, {'usernames_or_emails': 'user_1'},
                         instance=instance)
        instance = form.save()
        self.assertEqual(instance.shared_users.count(), 1)

        # Since save sends email asynchronously, wait for a while for the mail
        # to go through.
        time.sleep(5)

        # Make sure the user count is unaffected
        self.assertEqual(previous_user_count, User.objects.count())

        # Make sure no email was generated as a result
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(SERRANO_QUERY_REVERSE_NAME='serrano:queries:single')
    def test_clean_user_email_logging(self):
        """
        We override the SERRANO_QUERY_REVERSE_NAME setting here to avoid the
        setting not found warning in the forms code. This code counts the log
        warnings so we need to avoid triggering unnecessary warnings.
        """
        user = User.objects.create_user(username='user_1',
                                        email='user_1@email.com')
        user.save()

        initial_warning_count = len(self.mock_handler.messages['warning'])

        form = QueryForm(self.request, {'usernames_or_emails': ""})
        instance = form.save()
        self.assertEqual(instance.shared_users.count(), 0)
        self.assertEqual(len(self.mock_handler.messages['warning']),
                         initial_warning_count)

        initial_warning_count = len(self.mock_handler.messages['warning'])

        form = QueryForm(self.request, {'usernames_or_emails': 'user_1, \
            valid@email.com, ~~invalid_username~~, ~~invalid@email~~'})
        instance = form.save()
        self.assertEqual(instance.shared_users.count(), 2)
        self.assertEqual(len(self.mock_handler.messages['warning']),
                         initial_warning_count + 2)

    def test_warn_on_reverse_setting_missing(self):
        initial_warning_count = len(self.mock_handler.messages['warning'])

        form = QueryForm(self.request, {'usernames_or_emails': ""})
        instance = form.save()
        self.assertEqual(instance.shared_users.count(), 0)
        self.assertEqual(len(self.mock_handler.messages['warning']),
                         initial_warning_count + 1)

    @override_settings(SERRANO_QUERY_REVERSE_NAME='serrano:root')
    def test_warn_on_bad_reverse_setting(self):
        initial_warning_count = len(self.mock_handler.messages['warning'])

        form = QueryForm(self.request, {'usernames_or_emails': ""})
        instance = form.save()
        self.assertEqual(instance.shared_users.count(), 0)
        self.assertEqual(len(self.mock_handler.messages['warning']),
                         initial_warning_count + 1)

    def test_view_json(self):
        expected_count = Employee.objects.count()

        form = QueryForm(self.request, {'view_json': [{'concept': 1}]})
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(instance.record_count, expected_count)

    def test_context_json(self):
        expected_count = \
            Employee.objects.filter(title__salary__gt=1000).count()

        form = QueryForm(self.request, {'context_json': {
            'field': 'tests.title.salary', 'operator': 'gt', 'value': '1000'}})
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(instance.distinct_count, expected_count)

    def test_both_json(self):
        expected_count = \
            Employee.objects.filter(title__salary__gt=1000).count()

        form = QueryForm(self.request, {
            'context_json': {
                'field': 'tests.title.salary', 'operator': 'gt',
                'value': '1000'},
            'view_json': [{'concept': 1}]})
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(instance.distinct_count, expected_count)
        self.assertEqual(instance.record_count, expected_count)

    def test_force_count(self):
        expected_count = Employee.objects.distinct().count()

        form = QueryForm(self.request, {}, force_count=True)
        self.assertTrue(form.is_valid())

        instance = form.save()
        self.assertEqual(instance.distinct_count, expected_count)
        self.assertEqual(instance.record_count, expected_count)

    def test_no_commit(self):
        previous_user_count = User.objects.count()

        form = QueryForm(self.request,
                         {'usernames_or_emails': 'email1@email.com'})
        instance = form.save(commit=False)

        # Since save sends email asynchronously, wait for a while for the mail
        # to go through.
        time.sleep(5)

        # The instance should not be saved and shared_users should be
        # inaccessible on the model instance because the commit flag was False.
        self.assertIsNone(instance.pk)
        self.assertRaises(ValueError, lambda: instance.shared_users)

        # Make sure no users were created and no email was sent
        self.assertEqual(previous_user_count, User.objects.count())
        self.assertEqual(len(mail.outbox), 0)
