import json
from django.contrib.auth.models import User
from avocado.models import DataView
from .base import BaseTestCase


class ViewResourceTestCase(BaseTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test', password='test')
        self.client.login(username='test', password='test')

    def test_get_all(self):
        response = self.client.get('/api/views/',
            HTTP_ACCEPT='application/json')
        self.assertFalse(json.loads(response.content))

    def test_get_all_default(self):
        view = DataView(template=True, default=True, json={})
        view.save()
        response = self.client.get('/api/views/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 1)

    def test_get(self):
        view = DataView(user=self.user)
        view.save()
        response = self.client.get('/api/views/1/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content)
        self.assertLess(view.accessed,
                DataView.objects.get(pk=view.pk).accessed)
