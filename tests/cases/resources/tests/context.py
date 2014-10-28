import json
from restlib2.http import codes
from avocado.models import DataContext, DataField
from .base import AuthenticatedBaseTestCase


class ContextResourceTestCase(AuthenticatedBaseTestCase):
    def setUp(self):
        super(ContextResourceTestCase, self).setUp()

        self.salary_field = DataField.objects.get_by_natural_key(
            'tests', 'title', 'salary')

    def test_get_all(self):
        response = self.client.get('/api/contexts/',
                                   HTTP_ACCEPT='application/json')
        self.assertFalse(json.loads(response.content))

    def test_get_all_default(self):
        cxt = DataContext(template=True, default=True, json={})
        cxt.save()
        response = self.client.get('/api/contexts/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 1)

    def test_get(self):
        ctx = DataContext(user=self.user)
        ctx.save()
        response = self.client.get('/api/contexts/1/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(response.content)
        self.assertLess(ctx.accessed,
                        DataContext.objects.get(pk=ctx.pk).accessed)

        # Make sure that accessing a non-existent context returns a 404 error
        # indicating that it wasn't found.
        response = self.client.get('/api/contexts/999/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)

    def test_get_session(self):
        context = DataContext(user=self.user, name='Session Context',
                              session=True)
        context.save()

        response = self.client.get('/api/contexts/session/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(response.content)

        context.session = False
        context.save()

        response = self.client.get('/api/contexts/session/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)

    def test_post(self):
        # Attempt to create a new context using a POST request.
        response = self.client.post(
            '/api/contexts/',
            data=u'{"name":"POST Context"}',
            content_type='application/json')
        self.assertEqual(response.status_code, codes.created)

        # Make sure the changes from the POST request are persisted.
        response = self.client.get('/api/contexts/1/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        content = json.loads(response.content)
        self.assertTrue(content)
        self.assertEqual(content['name'], 'POST Context')
        self.assertEqual(content['count'], None)

        data = '''
        {{
            "name": "JSON Context",
            "json": {{
                "field": {0},
                "operator": "isnull",
                "value": false
            }}
        }}'''.format(self.salary_field.id)

        # Create a new context and include JSON so we get a count back.
        response = self.client.post(
            '/api/contexts/', data=data, content_type='application/json')
        content = json.loads(response.content)
        self.assertTrue(content)
        self.assertEqual(content['name'], 'JSON Context')
        self.assertEqual(content['count'], 6)

        # Now, use JSON and a custom processor and our count should differ
        # from the case where we just included JSON.
        response = self.client.post(
            '/api/contexts/?processor=manager',
            data=data,
            content_type='application/json')
        content = json.loads(response.content)
        self.assertTrue(content)
        self.assertEqual(content['name'], 'JSON Context')
        self.assertEqual(content['count'], 1)

        # Make a POST request with invalid JSON and make sure we get an
        # unprocessable status code back.
        response = self.client.post(
            '/api/contexts/',
            data=u'{"json":"[~][~]"}',
            content_type='application/json')
        self.assertEqual(response.status_code, codes.unprocessable_entity)

    def test_put(self):
        # Add a context so we can try to update it later.
        ctx = DataContext(user=self.user, name='Context 1')
        ctx.save()
        response = self.client.get('/api/contexts/1/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(response.content)

        # Attempt to update the name via a PUT request.
        response = self.client.put(
            '/api/contexts/1/',
            data=u'{"name":"New Name"}',
            content_type='application/json')
        self.assertEqual(response.status_code, codes.ok)

        # Make sure our changes from the PUT request are persisted and that
        # updating the name didn't trigger a count.
        response = self.client.get('/api/contexts/1/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        content = json.loads(response.content)
        self.assertTrue(content)
        self.assertEqual(content['name'], 'New Name')
        self.assertEqual(content['count'], None)

        data = '''
        {{
            "name": "JSON Context",
            "json": {{
                "field": {0},
                "operator": "isnull",
                "value": false
            }}
        }}'''.format(self.salary_field.id)

        # Now, change the JSON and check that the count changed.
        response = self.client.put(
            '/api/contexts/1/', data=data, content_type='application/json')
        content = json.loads(response.content)
        self.assertTrue(content)
        self.assertEqual(content['name'], 'JSON Context')
        self.assertEqual(content['count'], 6)

        data = '''
        {{
            "name": "JSON Context",
            "json": {{
                "field": {0},
                "operator": "gt",
                "value": 0
            }}
        }}'''.format(self.salary_field.id)

        # Tweak the JSON and use a query processor which should trigger a
        # count and also use the query processor's queryset when counting.
        response = self.client.put(
            '/api/contexts/1/?processor=manager',
            data=data,
            content_type='application/json')
        content = json.loads(response.content)
        self.assertTrue(content)
        self.assertEqual(content['name'], 'JSON Context')
        self.assertEqual(content['count'], 1)

        # Make a PUT request with invalid JSON and make sure we get an
        # unprocessable status code back.
        response = self.client.put(
            '/api/contexts/1/',
            data=u'{"json":"]]]"}',
            content_type='application/json')
        self.assertEqual(response.status_code, codes.unprocessable_entity)

    def test_delete(self):
        ctx = DataContext(user=self.user, name='Context 1')
        ctx.save()
        ctx = DataContext(user=self.user, name='Context 2')
        ctx.save()
        ctx = DataContext(user=self.user, name='Context 3', session=True)
        ctx.save()

        response = self.client.get('/api/contexts/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 3)

        response = self.client.delete('/api/contexts/1/')
        self.assertEqual(response.status_code, codes.no_content)

        response = self.client.get('/api/contexts/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 2)

        response = self.client.delete('/api/contexts/3/')
        self.assertEqual(response.status_code, codes.bad_request)

        response = self.client.get('/api/contexts/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 2)


class ContextStatsResourceTestCase(AuthenticatedBaseTestCase):
    def test_pk(self):
        cxt = DataContext(session=True, user=self.user)
        cxt.save()

        response = self.client.get('/api/contexts/1/stats/',
                                   HTTP_ACCEPT='application/json')

        self.assertEqual(json.loads(response.content)['count'], 6)

    def test_session(self):
        cxt = DataContext(session=True, user=self.user)
        cxt.save()

        response = self.client.get('/api/contexts/session/stats/',
                                   HTTP_ACCEPT='application/json')

        self.assertEqual(json.loads(response.content)['count'], 6)


class ContextsRevisionsResourceTestCase(AuthenticatedBaseTestCase):
    def test_get(self):
        ctx = DataContext(user=self.user)
        ctx.save()

        response = self.client.get('/api/contexts/revisions/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 1)
