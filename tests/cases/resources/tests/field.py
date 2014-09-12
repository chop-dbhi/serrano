import json
from django.test.utils import override_settings
from avocado.models import DataField
from avocado.events.models import Log
from restlib2.http import codes
from .base import BaseTestCase
from tests.models import Project, Title


class FieldResourceTestCase(BaseTestCase):
    def test_get_all(self):
        response = self.client.get('/api/fields/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 5)

    @override_settings(SERRANO_CHECK_ORPHANED_FIELDS=True)
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

        response = self.client.get('/api/fields/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 5)

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

    @override_settings(SERRANO_CHECK_ORPHANED_FIELDS=True)
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

        response = self.client.get('/api/fields/2/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)

    def test_get_privileged(self):
        # Superuser sees everything
        self.client.login(username='root', password='password')

        response = self.client.get('/api/fields/?unpublished=1',
            HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 12)

        response = self.client.get('/api/fields/1/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content))

    def test_values(self):
        # title.name
        response = self.client.get('/api/fields/2/values/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertTrue(content['values'])
        self.assertTrue(len(content['values']), 7)

        response = self.client.get(
            '/api/fields/2/values/?processor=first_title',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertTrue(content['values'])
        self.assertTrue(len(content['values']), 1)

    def test_values_no_limit(self):
        # title.name
        response = self.client.get('/api/fields/2/values/?limit=0',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['values'])
        self.assertFalse('previous' in data['_links'])
        self.assertFalse('next' in data['_links'])

    def test_values_random(self):
        # Random values
        response = self.client.get('/api/fields/2/values/?random=3',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 3)

        # Even though we are requesting 3 values, the query processor should
        # limit the population to 1 value so make sure that the call returns
        # only that single value since all values in the population should be
        # returned when the random sample size is bigger than population size.
        response = self.client.get(
            '/api/fields/2/values/?random=3&processor=first_title',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 1)

    def test_values_query(self):
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

        response = self.client.get(
            '/api/fields/2/values/?query=a&processor=under_twenty_thousand',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['values'], [
            {'label': 'Guard', 'value': 'Guard'},
            {'label': 'Programmer', 'value': 'Programmer'},
            {'label': 'QA', 'value': 'QA'},
        ])

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

    def test_labels_validate(self):
        # Valid, single dict
        response = self.client.post('/api/fields/2/values/',
            data=json.dumps({'label': 'IT'}),
            content_type='application/json',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(content, {
            'value': 'IT',
            'label': 'IT',
            'valid': True,
        })

    def test_mixed_validate(self):
        response = self.client.post('/api/fields/2/values/',
            data=json.dumps([
                {'label': 'IT'},
                {'label': 'Bartender'},
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

    def test_stats(self):
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
        stats = json.loads(response.content)
        self.assertTrue(stats)
        self.assertTrue(Log.objects.filter(event='stats', object_id=3).exists())
        self.assertEqual(stats['min'], 10000)
        self.assertEqual(stats['max'], 200000)
        self.assertAlmostEqual(stats['avg'], 53571.42857, places=5)

        # Using an invalid query processor should fall back to the default.
        response = self.client.get('/api/fields/3/stats/?processor=INVALID',
            HTTP_ACCEPT='application/json')
        stats = json.loads(response.content)
        self.assertEqual(stats['min'], 10000)
        self.assertEqual(stats['max'], 200000)
        self.assertAlmostEqual(stats['avg'], 53571.42857, places=5)

        # Using a valid query processor should affect the stats.
        response = self.client.get(
            '/api/fields/3/stats/?processor=under_twenty_thousand',
            HTTP_ACCEPT='application/json')
        stats = json.loads(response.content)
        self.assertEqual(stats['min'], 10000)
        self.assertEqual(stats['max'], 15000)
        self.assertEqual(stats['avg'], 13750)

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
        default_content = {
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
        }

        # title.salary
        response = self.client.get('/api/fields/3/dist/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), default_content)
        self.assertTrue(Log.objects.filter(event='dist', object_id=3).exists())

        # Using an invalid processor should fallback to the default processor.
        response = self.client.get('/api/fields/3/dist/?processor=INVALID',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(json.loads(response.content), default_content)

        # Using the custom query process, we should be limited to a smaller
        # salary set.
        response = self.client.get('/api/fields/3/dist/?processor=manager',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(json.loads(response.content), {
            u'size': 1,
            u'clustered': False,
            u'outliers': [],
            u'data': [{
                u'count': 1,
                u'values': [15000]
            }]
        })
