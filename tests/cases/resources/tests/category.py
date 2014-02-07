import json
from avocado.models import DataCategory
from avocado.events.models import Log
from .base import BaseTestCase


class CategoryResourceTestCase(BaseTestCase):
    def setUp(self):
        super(CategoryResourceTestCase, self).setUp()

        c1 = DataCategory(name='Title', published=True)
        c1.save()

        c2 = DataCategory(name='Other', published=False)
        c2.save()

    def test_get_all(self):
        response = self.client.get('/api/categories/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 1)

    def test_get_one(self):
        response = self.client.get('/api/categories/999/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 404)

        response = self.client.get('/api/categories/1/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content))
        self.assertTrue(Log.objects.filter(event='read', object_id=1).exists())

    def test_get_privileged(self):
        # Superuser sees everything
        self.client.login(username='root', password='password')

        response = self.client.get('/api/categories/?unpublished=1',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 2)

        response = self.client.get('/api/categories/2/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content))
