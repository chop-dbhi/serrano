import json
from restlib2.http import codes
from avocado.models import DataContext
from .base import AuthenticatedBaseTestCase


class ContextResourceTestCase(AuthenticatedBaseTestCase):
    def test_get_all(self):
        response = self.client.get('/api/contexts/',
                                   HTTP_ACCEPT='application/json')
        self.assertFalse(json.loads(response.content))
        self.assertEqual(response['Link-Template'], (
            '<http://testserver/api/contexts/{id}/stats/>; rel="stats", '
            '<http://testserver/api/contexts/{id}/>; rel="context"'
        ))

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
        content = json.loads(response.content)
        self.assertEqual(content['object_name'], 'employee')
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
        self.assertTrue(response.content)
        self.assertEqual(json.loads(response.content)['name'], 'POST Context')

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

        # Make sure our changes from the PUT request are persisted.
        response = self.client.get('/api/contexts/1/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(response.content)
        self.assertEqual(json.loads(response.content)['name'], 'New Name')

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

    def test_processor(self):
        cxt = DataContext(session=True, user=self.user)
        cxt.save()

        response = self.client.get('/api/contexts/1/stats/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(json.loads(response.content)['count'], 6)

        response = self.client.get('/api/contexts/1/stats/?processor=manager',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(json.loads(response.content)['count'], 1)


class ContextsRevisionsResourceTestCase(AuthenticatedBaseTestCase):
    def test_get(self):
        ctx = DataContext(user=self.user)
        ctx.save()

        response = self.client.get('/api/contexts/revisions/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 1)
