import json
from restlib2.http import codes
from avocado.models import DataContext
from .base import AuthenticatedBaseTestCase


class ContextResourceTestCase(AuthenticatedBaseTestCase):
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



class ContextsRevisionsResourceTestCase(AuthenticatedBaseTestCase):
    def test_get(self):
        ctx = DataContext(user=self.user)
        ctx.save()

        response = self.client.get('/api/contexts/revisions/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 1)
