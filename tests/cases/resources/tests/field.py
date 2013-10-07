import json
from django.test.utils import override_settings
from avocado.models import DataField, Log
from .base import BaseTestCase
from tests.models import Project, Title

class FieldResourceTestCase(BaseTestCase):
    def test_get_all(self):
        response = self.client.get('/api/fields/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 5)

    def test_get_all_orphan(self):
        # Orphan one of the fields we are about to retrieve
        DataField.objects.filter(pk=2).update(field_name="XXX")

        response = self.client.get('/api/fields/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 4)

    @override_settings(SERRANO_CHECK_ORPHANED_FIELDS=False)
    def test_get_all_orphan_check_off(self):
        # Orphan one of the fields we are about to retrieve
        DataField.objects.filter(pk=2).update(field_name="XXX")

        self.assertRaises(AttributeError, self.client.get, '/api/fields/',
            HTTP_ACCEPT='application/json')

    def test_get_one(self):
        # Not allowed to see
        response = self.client.get('/api/fields/1/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 404)

        response = self.client.get('/api/fields/2/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content))
        self.assertTrue(Log.objects.filter(event='read', object_id=2).exists())

    def test_get_one_orphan(self):
        # Orphan the field before we retrieve it
        DataField.objects.filter(pk=2).update(model_name="XXX")

        response = self.client.get('/api/fields/2/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 500)

    @override_settings(SERRANO_CHECK_ORPHANED_FIELDS=False)
    def test_get_one_orphan_check_off(self):
        # Orphan one of the fields we are about to retrieve
        DataField.objects.filter(pk=2).update(field_name="XXX")

        self.assertRaises(AttributeError, self.client.get, '/api/fields/2/',
            HTTP_ACCEPT='application/json')

    def test_get_privileged(self):
        # Superuser sees everything
        self.client.login(username='root', password='password')

        response = self.client.get('/api/fields/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 11)

        response = self.client.get('/api/fields/1/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content))

    def test_values(self):
        # title.name
        response = self.client.get('/api/fields/2/values/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)['values'])

    def test_values_random(self):
        # Random values
        response = self.client.get('/api/fields/2/values/?random=3',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 3)

    def test_values_query(self):
        # Query values
        response = self.client.get('/api/fields/2/values/?query=a',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['values'], [
            {'label': 'Analyst', 'value': 'Analyst'},
            {'label': 'Guard', 'value': 'Guard'},
            {'label': 'Lawyer', 'value': 'Lawyer'},
            {'label': 'Programmer', 'value': 'Programmer'},
            {'label': 'QA', 'value': 'QA'},
        ])
        message = Log.objects.get(event='values', object_id=2)
        self.assertEqual(message.data['query'], 'a')

    def test_values_validate(self):
        # Valid, single dict
        response = self.client.post('/api/fields/2/values/',
            data=json.dumps({'value': 'IT'}),
            content_type='application/json',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(content, {
            'value': 'IT',
            'label': 'IT',
            'valid': True,
        })
        message = Log.objects.get(event='validate', object_id=2)
        self.assertEqual(message.data['count'], 1)

        # Invalid
        response = self.client.post('/api/fields/2/values/',
            data=json.dumps({'value': 'Bartender'}),
            content_type='application/json',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(content, {
            'value': 'Bartender',
            'label': 'Bartender',
            'valid': False,
        })

        # Mixed, list
        response = self.client.post('/api/fields/2/values/',
            data=json.dumps([
                {'value': 'IT'},
                {'value': 'Bartender'},
                {'value': 'Programmer'}
            ]),
            content_type='application/json',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(content, [
            {'value': 'IT', 'label': 'IT', 'valid': True},
            {'value': 'Bartender', 'label': 'Bartender', 'valid': False},
            {'value': 'Programmer', 'label': 'Programmer', 'valid': True},
        ])

        # Error - no value
        response = self.client.post('/api/fields/2/values/',
            data=json.dumps({}),
            content_type='application/json',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 422)

        # Error - type
        response = self.client.post('/api/fields/2/values/',
            data=json.dumps(None),
            content_type='application/json',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 422)

    @override_settings(AVOCADO_DATA_CACHE_ENABLED=False)
    def test_stats(self):
        """
        There is a bug in the CacheProxy in Avocado so we need to disable the
        data cache for these tests. See the following for more info:

            https://github.com/cbmi/avocado/issues/136
        """

        # title.name
        response = self.client.get('/api/fields/2/stats/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content))
        self.assertTrue(Log.objects.filter(event='stats', object_id=2).exists())

        # title.salary
        response = self.client.get('/api/fields/3/stats/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content))
        self.assertTrue(Log.objects.filter(event='stats', object_id=3).exists())

        # project.due_date
        response = self.client.get('/api/fields/11/stats/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)

        stats = json.loads(response.content)

        self.assertTrue(stats)
        self.assertTrue(Log.objects.filter(event='stats', object_id=11).exists())
        self.assertEqual(stats['min'], '2000-01-01')
        self.assertEqual(stats['max'], '2010-01-01')

    def test_empty_stats(self):
        Title.objects.all().delete()

        response = self.client.get('/api/fields/2/stats/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content))
        self.assertTrue(Log.objects.filter(event='stats', object_id=2).exists())

    def test_dist(self):
        # title.salary
        response = self.client.get('/api/fields/3/dist/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {
            u'size': 4,
            u'clustered': False,
            u'outliers': [],
            u'data': [{
                u'count': 3,
                u'values': [15000]
            }, {
                u'count': 1,
                u'values': [10000]
            }, {
                u'count': 1,
                u'values': [20000]
            }, {
                u'count': 1,
                u'values': [200000]
            }],
        })
        self.assertTrue(Log.objects.filter(event='dist', object_id=3).exists())
