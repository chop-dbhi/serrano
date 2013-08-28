import json
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from avocado.history.models import Revision
from avocado.models import DataContext
from .base import AuthenticatedBaseTestCase


class ContextResource(AuthenticatedBaseTestCase):
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
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content)
        self.assertLess(ctx.accessed,
                DataContext.objects.get(pk=ctx.pk).accessed)


class ContextsRevisionsResourceTestCase(AuthenticatedBaseTestCase):
    def test_get(self):
        ctx = DataContext(user=self.user)
        ctx.save()

        response = self.client.get('/api/contexts/revisions/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 1)
