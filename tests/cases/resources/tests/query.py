# -*- coding: utf-8 -*-

import json
import time
from django.contrib.auth.models import User
from django.core import mail
from restlib2.http import codes
from avocado.models import DataQuery
from .base import AuthenticatedBaseTestCase, BaseTestCase


class QueriesResourceTestCase(AuthenticatedBaseTestCase):
    def test_shared_users_count(self):
        u1 = User(username='user1', email='user1@email.com')
        u1.save()
        u2 = User(username='user2', email='user2@email.com')
        u2.save()

        query = DataQuery(user=self.user)
        query.save()
        query.shared_users.add(u1)
        query.shared_users.add(u2)
        query.save()

        response = self.client.get('/api/queries/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 1)
        self.assertEqual(response['Link-Template'], (
            '<http://testserver/api/queries/{id}/>; rel="self", '
            '<http://testserver/api/queries/{id}/stats/>; rel="stats", '
            '<http://testserver/api/queries/{id}/forks/>; rel="forks", '
            '<http://testserver/api/queries/{id}/results/>; rel="results"'
        ))

        content = json.loads(response.content)[0]
        self.assertEqual(len(content['shared_users']), 2)

        u3 = User(username='user3', email='user3@email.com')
        u3.save()
        u4 = User(username='user4', email='user4@email.com')
        u4.save()

        query.shared_users.remove(u1)
        query.shared_users.add(u3)
        query.shared_users.add(u4)
        query.save()

        response = self.client.get('/api/queries/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 1)

        content = json.loads(response.content)[0]
        self.assertEqual(len(content['shared_users']), 3)

    def test_session_owner(self):
        # No user for this one..
        self.client.logout()

        # Access endpoint to initialize the anonymous session. This feels
        # like a hack, but there seems to be no other way to initialize the
        # session with a key
        self.client.get('/api/')

        # Fake the session key
        query = DataQuery(session_key=self.client.session.session_key)
        query.save()

        response = self.client.get('/api/queries/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 1)

        query = json.loads(response.content)[0]
        self.assertTrue(query['is_owner'])

    def test_only_owner(self):
        query = DataQuery(user=self.user)
        query.save()

        query2 = DataQuery()
        query2.save()

        # Ensure that there are 2 queries to start
        self.assertEqual(DataQuery.objects.count(), 2)

        response = self.client.get('/api/queries/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 1)

        query = json.loads(response.content)[0]
        self.assertTrue(query['is_owner'])
        self.assertTrue('shared_users' in query)

    def test_owner_and_shared(self):
        # Create a query this user owns
        query = DataQuery(user=self.user)
        query.save()

        # Create a query owned by and shared with no one
        query2 = DataQuery()
        query2.save()

        # Create a query with no owner but shared with this user
        query3 = DataQuery()
        query3.save()
        query3.shared_users.add(self.user)
        query3.save()

        self.assertEqual(DataQuery.objects.count(), 3)

        # Retrieve the queries shared with and owned by this user, the count
        # should be 2 since this user owns one and is the sharee on another.
        response = self.client.get('/api/queries/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 2)

        # Verify that the order is descending based on accessed time. The 3rd
        # query was created most recently so it should be first in the list
        # over the 1st query.
        shared_queries = json.loads(response.content)
        self.assertEqual(shared_queries[0]['id'], query3.pk)
        self.assertEqual(shared_queries[1]['id'], query.pk)

        # Access the 1st query. This should make its accessed time update thus
        # making the 1st query the most recent of this users' shared queries.
        response = self.client.get('/api/queries/{0}/'.format(query.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)

        # Retrieve the queries shared with and owned by this user once again
        # to make sure the order has changed.
        response = self.client.get('/api/queries/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 2)

        # Since the 1st query was just accessed, it should now be the first
        # query in the result followed by the 3rd query.
        shared_queries = json.loads(response.content)
        self.assertEqual(shared_queries[0]['id'], query.pk)
        self.assertEqual(shared_queries[1]['id'], query3.pk)

        # If we logout and submit the request without a user, there should
        # be 0 shared queries returned.
        self.client.logout()
        response = self.client.get('/api/queries/',
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

        response = self.client.get('/api/queries/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 1)

        query = json.loads(response.content)[0]
        self.assertFalse(query['is_owner'])
        self.assertFalse('shared_users' in query)

    def test_post(self):
        # Attempt to create a new query using a POST request
        response = self.client.post('/api/queries/',
                                    data=u'{"name":"POST Query"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, codes.created)
        data = json.loads(response.content)

        # Make sure the changes from the POST request are persisted
        response = self.client.get('/api/queries/{0}/'.format(data['id']),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(response.content)
        self.assertEqual(json.loads(response.content)['name'], 'POST Query')

        # Make a POST request with invalid JSON and make sure we get an
        # unprocessable status code back.
        response = self.client.post('/api/queries/',
                                    data=u'{"view_json":"[~][~]"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, codes.unprocessable_entity)

    def test_post_with_email(self):
        u1 = User(username='user1', email='user1@email.com')
        u1.save()
        u2 = User(username='user2', email='user2@email.com')
        u2.save()

        outbox_count = len(mail.outbox)
        data = '{"name":"POST Query","message":"THIS IS ONLY A TEST!",'\
               '"usernames_or_emails":"user1,user2@email.com"}'
        response = self.client.post(
            '/api/queries/', data=data, content_type='application/json')
        self.assertEqual(response.status_code, codes.created)

        self.assertEqual(len(mail.outbox), outbox_count + 1)
        self.assertEqual(mail.outbox[0].subject,
                         'example.com: POST Query has been shared with you!')
        self.assertEqual(mail.outbox[0].body,
                         'THIS IS ONLY A TEST!\n\n--\nView the query at '
                         'http://testserver/')
        self.assertSequenceEqual(
            mail.outbox[0].to, ['user1@email.com', 'user2@email.com'])


class PublicQueriesResourceTestCase(BaseTestCase):
    def test_get(self):
        query = DataQuery(name='Q1', public=True)
        query.save()

        query = DataQuery(name='Q2', public=True)
        query.save()

        query = DataQuery(name='Q3')
        query.save()

        self.assertEqual(DataQuery.objects.distinct().count(), 3)

        response = self.client.get('/api/queries/public/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(response.content)
        self.assertEqual(len(json.loads(response.content)), 2)


class QueryForksResourceTestCase(AuthenticatedBaseTestCase):
    def setUp(self):
        super(QueryForksResourceTestCase, self).setUp()

        self.public_query = DataQuery(name='Public Parent', public=True)
        self.public_query.save()

        self.user_query = DataQuery(name='Private User Parent', user=self.user)
        self.user_query.save()

        self.private_query = DataQuery(name='Private Parent')
        self.private_query.save()

        self.query = DataQuery(name='Shared Parent')
        self.query.save()
        self.query.shared_users.add(self.user)
        self.query.save()

        query = DataQuery(name='Child 1', parent=self.public_query)
        query.save()
        query = DataQuery(name='Child 2', parent=self.public_query)
        query.save()
        query = DataQuery(name='Child 3', parent=self.public_query)
        query.save()

        query = DataQuery(name='Child 4', parent=self.user_query)
        query.save()
        query = DataQuery(name='Child 5', parent=self.user_query)
        query.save()

        query = DataQuery(name='Child 6', parent=self.private_query)
        query.save()

    def test_post(self):
        query_count = DataQuery.objects.count()

        # We should be able to fork public queries
        url = '/api/queries/{0}/forks/'.format(self.public_query.pk)
        response = self.client.post(url, data='{}',
                                    content_type='application/json',
                                    HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.created)
        self.assertEqual(DataQuery.objects.count(), query_count + 1)

        # ... and queries we own
        url = '/api/queries/{0}/forks/'.format(self.user_query.pk)
        response = self.client.post(url, data='{}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, codes.created)
        self.assertEqual(DataQuery.objects.count(), query_count + 2)

        # ... and queries shared with us
        url = '/api/queries/{0}/forks/'.format(self.query.pk)
        response = self.client.post(url, data='{}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, codes.created)
        self.assertEqual(DataQuery.objects.count(), query_count + 3)

    def test_post_unauthenticated(self):
        self.client.logout()

        url = '/api/queries/{0}/forks/'.format(self.user_query.pk)
        response = self.client.post(url, data='{}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, codes.unauthorized)

    def test_post_unauthorized(self):
        url = '/api/queries/{0}/forks/'.format(self.private_query.pk)
        response = self.client.post(url, data='{}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, codes.unauthorized)

    def test_post_invalid_pk(self):
        response = self.client.post('/api/queries/999999/forks/', data='{}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, codes.not_found)

    def test_get_invalid_pk(self):
        response = self.client.get('/api/queries/999999/forks/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)

    def test_get_authenticated_owner(self):
        url = '/api/queries/{0}/forks/'.format(self.user_query.pk)

        response = self.client.get(url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(response.content)
        self.assertEqual(len(json.loads(response.content)), 2)

    def test_get_unauthenticated_owner(self):
        self.client.logout()

        url = '/api/queries/{0}/forks/'.format(self.user_query.pk)

        response = self.client.get(url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.unauthorized)

    def test_get_public(self):
        url = '/api/queries/{0}/forks/'.format(self.public_query.pk)

        response = self.client.get(url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(response.content)
        self.assertEqual(len(json.loads(response.content)), 3)
        self.assertEqual(response['Link-Template'], (
            '<http://testserver/api/queries/{id}/>; rel="self", '
            '<http://testserver/api/queries/{parent_id}/>; rel="parent"'
        ))

    def test_get_unauthorized(self):
        url = '/api/queries/{0}/forks/'.format(self.private_query.pk)

        response = self.client.get(url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.unauthorized)


class QueryResourceTestCase(AuthenticatedBaseTestCase):
    def test_get(self):
        query = DataQuery(user=self.user)
        query.save()

        child_query = DataQuery(name='Child 1', parent=query)
        child_query.save()
        child_query = DataQuery(name='Child 2', parent=query)
        child_query.save()

        url = '/api/queries/{0}/'.format(query.pk)
        response = self.client.get(url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(response.content)
        self.assertLess(query.accessed,
                        DataQuery.objects.get(pk=query.pk).accessed)

        # When we access a query it should contain a valid link to the forks
        # of that query.
        self.assertTrue('forks' in response['Link-Template'])
        links = response['Link-Template'].split(',')

        for link in links:
            if 'forks' in link:
                # NOTE: This link template formatting would normally be done
                # on the client side but we do it manually once here to extract
                # and format the link to the forks.
                fields = link.split(';')
                href = fields[0].replace('<', '')\
                                .replace('>', '')\
                                .replace('{id}', str(query.pk))\
                                .strip()

                response = self.client.get(
                    href, HTTP_ACCEPT='application/json')
                self.assertEqual(response.status_code, codes.ok)
                self.assertTrue(response.content)
                self.assertEqual(len(json.loads(response.content)), 2)

        # Make sure we get a codes.not_found when accessing a query that
        # doesn't exist
        response = self.client.get('/api/queries/123456/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)

    def test_get_session(self):
        query = DataQuery(user=self.user, name='Query', session=True)
        query.save()

        response = self.client.get('/api/queries/session/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(response.content)

        query.session = False
        query.save()

        response = self.client.get('/api/queries/session/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)

    def test_put(self):
        # Add a query so we can try to update it later
        query = DataQuery(user=self.user, name='Query 1')
        query.save()
        response = self.client.get('/api/queries/{0}/'.format(query.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(response.content)

        # Attempt to update the name via a PUT request
        response = self.client.put('/api/queries/{0}/'.format(query.pk),
                                   data=u'{"name":"New Name"}',
                                   content_type='application/json')
        self.assertEqual(response.status_code, codes.ok)

        # Make sure our changes from the PUT request are persisted
        response = self.client.get('/api/queries/{0}/'.format(query.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(response.content)
        self.assertEqual(json.loads(response.content)['name'], 'New Name')

        # Make a PUT request with invalid JSON and make sure we get an
        # unprocessable status code back.
        response = self.client.put('/api/queries/{0}/'.format(query.pk),
                                   data=u'{"view_json":"[~][~]"}',
                                   content_type='application/json')
        self.assertEqual(response.status_code, codes.unprocessable_entity)

    def test_delete(self):
        query_name = u'ĘƞĵôƔ ťƕîš ǫųęŕƳ'

        query = DataQuery(user=self.user, name=query_name)
        query.save()
        session_query = DataQuery(user=self.user, name="SessionQuery",
                                  session=True)
        session_query.save()

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
        self.assertEqual(len(json.loads(response.content)), 2)

        response = self.client.delete('/api/queries/{0}/'.format(query.pk),
                                      HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.no_content)

        # Since the delete handler send email asynchronously, wait for a while
        # while the mail goes through.
        time.sleep(5)

        # Make sure the mail was sent
        self.assertEqual(len(mail.outbox), 1)
        # Make sure the subject is correct
        self.assertEqual(mail.outbox[0].subject,
                         u"'{0}' has been deleted".format(query_name))
        # Make sure the recipient list is correct
        self.assertSequenceEqual(
            mail.outbox[0].to, ['share@example.com', '', 'share3@example.com'])

        response = self.client.get('/api/queries/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 1)

        # Make sure that we cannot delete the session query
        response = self.client.delete('/api/queries/{0}/'
                                      .format(session_query.pk))
        self.assertEqual(response.status_code, codes.bad_request)

        response = self.client.get('/api/queries/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 1)


class QueryStatsResourceTestCase(AuthenticatedBaseTestCase):
    def test_pk(self):
        query = DataQuery(session=True, user=self.user)
        query.save()

        response = self.client.get('/api/queries/{0}/stats/'.format(query.pk),
                                   HTTP_ACCEPT='application/json')

        data = json.loads(response.content)
        self.assertEqual(data['distinct_count'], 6)
        self.assertEqual(data['record_count'], 6)

    def test_session(self):
        query = DataQuery(session=True, user=self.user)
        query.save()

        response = self.client.get('/api/queries/session/stats/',
                                   HTTP_ACCEPT='application/json')

        data = json.loads(response.content)
        self.assertEqual(data['distinct_count'], 6)
        self.assertEqual(data['record_count'], 6)

    def test_processor(self):
        query = DataQuery(session=True, user=self.user)
        query.save()

        response = self.client.get('/api/queries/{0}/stats/'.format(query.pk),
                                   HTTP_ACCEPT='application/json')
        data = json.loads(response.content)
        self.assertEqual(data['distinct_count'], 6)
        self.assertEqual(data['record_count'], 6)

        response = self.client.get('/api/queries/{0}/stats/?processor=manager'
                                   .format(query.pk),
                                   HTTP_ACCEPT='application/json')
        data = json.loads(response.content)
        self.assertEqual(data['distinct_count'], 1)
        self.assertEqual(data['record_count'], 1)


class EmailTestCase(BaseTestCase):
    subject = 'Email_Subject'
    message = str([i for i in range(5000)])

    def test_synchronous(self):
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
        self.assertSequenceEqual(
            mail.outbox[0].to, ['share@example.com', '', 'share3@example.com'])

    def test_asynchronous(self):
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
        # "asynchronousness".
        time.sleep(5)
        self.assertEqual(len(mail.outbox), 1)
        # Make sure the subject is correct
        self.assertEqual(mail.outbox[0].subject, self.subject)
        self.assertEqual(mail.outbox[0].body, self.message)
        # Make sure the recipient list is correct
        self.assertSequenceEqual(
            mail.outbox[0].to, ['share@example.com', '', 'share3@example.com'])


class QueriesRevisionsResourceTestCase(AuthenticatedBaseTestCase):
    def test_get(self):
        query = DataQuery(user=self.user)
        query.save()

        response = self.client.get('/api/queries/revisions/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 1)


class QueryResultsResourceTestCase(AuthenticatedBaseTestCase):
    def setUp(self):
        super(QueryResultsResourceTestCase, self).setUp()

        self.query = DataQuery(user=self.user)
        self.query.save()

    def test_get(self):
        response = self.client.get(
            '/api/queries/{0}/results/'.format(self.query.id),
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)

        # Let's just make sure that we didn't break anything regarding making
        # sure the query exists.
        response = self.client.get('api/queries/999/results/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)

    def test_get_session(self):
        query = DataQuery(user=self.user, name='Query', session=True)
        query.save()

        # All results for session query.
        response = self.client.get('/api/queries/session/results/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(response.content)

        # Single page of results for session query.
        response = self.client.get('/api/queries/session/results/3/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(response.content)

        # Page range of results for session query.
        response = self.client.get('/api/queries/session/results/1...5/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(response.content)

        query.session = False
        query.save()

        response = self.client.get('/api/queries/session/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)

    def test_page(self):
        # Page numbers must be greater than or equal to 1.
        response = self.client.get(
            '/api/queries/{0}/results/0/'.format(self.query.id),
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)

        # Pages greater than 0 should be fine.
        response = self.client.get(
            '/api/queries/{0}/results/3/'.format(self.query.id),
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)

    def test_page_range(self):
        # When using a page range, a 0 page should still be invalid.
        response = self.client.get(
            '/api/queries/{0}/results/0...3/'.format(self.query.id),
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)

        # Stop pages less than start pages aren't a valid range.
        response = self.client.get(
            '/api/queries/{0}/results/3...1/'.format(self.query.id),
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)

        # Stop pages >= start pages should be valid.
        response = self.client.get(
            '/api/queries/{0}/results/3...50/'.format(self.query.id),
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)

    def test_delete(self):
        # There is nothing to delete here so we should be OK.
        response = self.client.delete(
            '/api/queries/{0}/results/'.format(self.query.id),
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(
            json.loads(response.content),
            {'canceled': None}
        )

        # This should start an isolated query.
        response = self.client.get(
            '/api/queries/{0}/results/'.format(self.query.id),
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)

        # The above GET request should have created an isolated query. So, we
        # get a value indicating that we have canceled it here.
        response = self.client.delete(
            '/api/queries/{0}/results/'.format(self.query.id),
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(
            json.loads(response.content),
            {'canceled': True}
        )
