import json
from avocado.models import DataCategory
from avocado.events.models import Log
from restlib2.http import codes
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
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 1)

    def test_get_one(self):
        response = self.client.get('/api/categories/999/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)

        response = self.client.get('/api/categories/1/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(json.loads(response.content))
        self.assertEqual(response['Link-Template'], (
            '<http://testserver/api/categories/{id}/>; rel="category", '
            '<http://testserver/api/categories/{parent_id}/>; rel="parent"'
        ))
        self.assertTrue(Log.objects.filter(event='read', object_id=1).exists())

    def test_get_privileged(self):
        # Superuser sees everything
        self.client.login(username='root', password='password')

        response = self.client.get('/api/categories/?unpublished=1',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 2)

        response = self.client.get('/api/categories/2/?unpublished=1',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(json.loads(response.content))

        # Make sure the unpublished categories are only exposed when explicitly
        # asked for even when a superuser makes the request.
        response = self.client.get('/api/categories/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 1)

        response = self.client.get('/api/categories/2/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)
