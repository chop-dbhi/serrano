import json, time
from django.contrib.auth.models import User
from django.core import mail
from django.test.utils import override_settings
from avocado.models import DataQuery
from .base import AuthenticatedBaseTestCase, BaseTestCase

class SharedQueryTestCase(AuthenticatedBaseTestCase):
    def test_only_owner(self):
        query = DataQuery(user=self.user)
        query.save()

        query2 = DataQuery()
        query2.save()

        # Ensure that there are 2 queries to start
        self.assertEqual(DataQuery.objects.count(), 2)

        response = self.client.get('/api/queries/shared/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 1)

        shared_query = json.loads(response.content)[0]
        self.assertTrue(shared_query['is_owner'])

    def test_owner_and_shared(self):
        query = DataQuery()
        query.save()
        query.shared_users.add(self.user)
        query.save()

        query2 = DataQuery()
        query2.save()

        query3 = DataQuery(user=self.user)
        query3.save()

        self.assertEqual(DataQuery.objects.count(), 3)

        response = self.client.get('/api/queries/shared/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 2)

        self.client.logout()
        response = self.client.get('/api/queries/shared/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 0)

    def test_only_shared(self):
        query = DataQuery()
        query.save()
        query.shared_users.add(self.user)
        query.save()

        query2 = DataQuery()
        query2.save()

        # Ensure that there are 2 queries to start
        self.assertEqual(DataQuery.objects.count(), 2)

        response = self.client.get('/api/queries/shared/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 1)

        shared_query = json.loads(response.content)[0]
        self.assertFalse(shared_query['is_owner'])

    @override_settings(SERRANO_AUTH_REQUIRED=True)
    def test_require_login(self):
        response = self.client.get('/api/queries/shared/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)

        self.client.logout()
        response = self.client.get('/api/queries/shared/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 401)


class QueryResourceTestCase(AuthenticatedBaseTestCase):
    def test_get_all(self):
        response = self.client.get('/api/queries/',
            HTTP_ACCEPT='application/json')
        self.assertFalse(json.loads(response.content))

    def test_get_all_default(self):
        query = DataQuery(template=True, default=True, json={})
        query.save()
        response = self.client.get('/api/queries/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 1)

    def test_get(self):
        query = DataQuery(user=self.user)
        query.save()
        response = self.client.get('/api/queries/1/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content)
        self.assertLess(query.accessed,
                DataQuery.objects.get(pk=query.pk).accessed)

    def test_shared_user(self):
        query = DataQuery(user=self.user)
        query.save()
        sharee = User(username='sharee', first_name='Shared',
            last_name='User', email='share@example.com')
        sharee.save()
        query.shared_users.add(sharee)
        response = self.client.get('/api/queries/1/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(json.loads(response.content)['shared_users'][0], {
            'id': sharee.id,
            'username': sharee.username,
            'name': sharee.get_full_name(),
            'email': sharee.email,
        })

    def test_delete(self):
        query = DataQuery(user=self.user, name="TestQuery")
        query.save()

        user1 = User(username='u1', first_name='Shared', last_name='User',
            email='share@example.com')
        user1.save()
        query.shared_users.add(user1)
        user2 = User(username='u2', first_name='Shared', last_name='User',
            email='')
        user2.save()
        query.shared_users.add(user2)
        user3 = User(username='u3', first_name='Shared', last_name='User',
            email='share3@example.com')
        user3.save()
        query.shared_users.add(user3)

        response = self.client.get('/api/queries/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 1)

        response = self.client.delete('/api/queries/1/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 204)

        # Since the delete handler send email asyncronously, wait for a while
        # while the mail goes through.
        time.sleep(5)

        # Make sure the mail was sent
        self.assertEqual(len(mail.outbox), 1)
        # Make sure the subject is correct
        self.assertEqual(mail.outbox[0].subject,
            "'TestQuery' has been deleted")
        # Make sure the recipient list is correct
        self.assertSequenceEqual(mail.outbox[0].to,
            ['share@example.com', '', 'share3@example.com'])

        response = self.client.get('/api/queries/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 0)


class EmailTestCase(BaseTestCase):
    subject = 'Email_Subject'
    message = str([i for i in range(5000)])

    def test_syncronous(self):
        from serrano.utils import send_mail
        user1 = User(username='u1', first_name='Shared', last_name='User',
            email='share@example.com')
        user2 = User(username='u2', first_name='Shared', last_name='User',
            email='')
        user3 = User(username='u3', first_name='Shared', last_name='User',
            email='share3@example.com')

        send_mail([user1.email, user2.email, user3.email], self.subject,
            self.message, async=False)

        # Make sure the mail was sent
        self.assertEqual(len(mail.outbox), 1)
        # Make sure the subject is correct
        self.assertEqual(mail.outbox[0].subject, self.subject)
        self.assertEqual(mail.outbox[0].body, self.message)
        # Make sure the recipient list is correct
        self.assertSequenceEqual(mail.outbox[0].to,
            ['share@example.com', '', 'share3@example.com'])

    def test_asyncronous(self):
        from serrano.utils import send_mail
        user1 = User(username='u1', first_name='Shared', last_name='User',
            email='share@example.com')
        user2 = User(username='u2', first_name='Shared', last_name='User',
            email='')
        user3 = User(username='u3', first_name='Shared', last_name='User',
            email='share3@example.com')

        send_mail([user1.email, user2.email, user3.email], self.subject,
            self.message)

        # Make sure the mail was sent(after a slight pause to account for the
        # "asyncronousness".
        time.sleep(5)
        self.assertEqual(len(mail.outbox), 1)
        # Make sure the subject is correct
        self.assertEqual(mail.outbox[0].subject, self.subject)
        self.assertEqual(mail.outbox[0].body, self.message)
        # Make sure the recipient list is correct
        self.assertSequenceEqual(mail.outbox[0].to,
            ['share@example.com', '', 'share3@example.com'])


class QueriesRevisionsResourceTestCase(AuthenticatedBaseTestCase):
    def test_get(self):
        query = DataQuery(user=self.user)
        query.save()

        response = self.client.get('/api/queries/revisions/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 1)
