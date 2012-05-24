from django.test import TestCase


class ResourceTestCase(TestCase):
    def test_no_auth(self):
        resp = self.client.get('/fields/')
        self.assertEqual(resp.status_code, 200)
