import json
from avocado.models import DataCategory
from avocado.events.models import Log
from .base import BaseTestCase


class CategoryResourceTestCase(BaseTestCase):
    def setUp(self):
        c = DataCategory(name='Title', published=True)
        c.save()

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
