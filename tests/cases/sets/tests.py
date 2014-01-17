import json
from django.test import TestCase
from django.core import management
from ...models import Team, Employee


class SetResourcesTest(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        management.call_command('avocado', 'init', 'tests', quiet=True)

    def test_root(self):
        response = self.client.get('/api/sets/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 1)

    def test_type(self):
        response = self.client.get('/api/sets/teams/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 0)

    def test_type_instance(self):
        Team(Employee.objects.all(), save=True)
        response = self.client.get('/api/sets/teams/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 1)

    def test_context(self):
        response = self.client.post('/api/sets/teams/', json.dumps({
            'context': {
                'field': 'tests.title.salary',
                'operator': 'gt',
                'value': 15000,
            }
        }), content_type='application/json',
            HTTP_ACCEPT='application/json')

        self.assertEqual(Employee.objects.filter(title__salary__gt=15000)
                         .count(), 2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['count'], 2)
