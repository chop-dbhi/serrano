import json
from avocado.models import DataCategory
from avocado.events.models import Log
from restlib2.http import codes
from .base import BaseTestCase


class CategoryResourceTestCase(BaseTestCase):
    def setUp(self):
        super(CategoryResourceTestCase, self).setUp()

        self.c1 = DataCategory(name='Title', published=True)
        self.c1.save()

        self.c2 = DataCategory(name='Other', published=False)
        self.c2.save()

    def test_get_all(self):
        response = self.client.get('/api/categories/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 1)

    def test_get_one(self):
        response = self.client.get('/api/categories/999/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)

        response = self.client.get('/api/categories/{0}/'.format(self.c1.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(json.loads(response.content))
        self.assertEqual(response['Link-Template'], (
            '<http://testserver/api/categories/{id}/>; rel="self", '
            '<http://testserver/api/categories/{parent_id}/>; rel="parent"'
        ))

        event = Log.objects.filter(event='read', object_id=self.c1.pk)
        self.assertTrue(event.exists())

    def test_get_privileged(self):
        self.client.login(username='root', password='password')

        response = self.client.get('/api/categories/?unpublished=1',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 2)

        response = self.client.get('/api/categories/{0}/?unpublished=1'
                                   .format(self.c2.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(json.loads(response.content))

        # Make sure the unpublished categories are only exposed when explicitly
        # asked for even when a superuser makes the request.
        response = self.client.get('/api/categories/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 1)

        response = self.client.get('/api/categories/{0}/'.format(self.c2.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)
