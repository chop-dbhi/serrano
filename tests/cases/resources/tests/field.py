import json
from django.test.utils import override_settings
from avocado.models import DataField
from avocado.events.models import Log
from restlib2.http import codes
from .base import BaseTestCase
from tests.models import Title


class FieldResourceTestCase(BaseTestCase):
    def test_get_all(self):
        response = self.client.get('/api/fields/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 5)

        self.assertEqual(response['Link-Template'], (
            '<http://testserver/api/fields/{id}/stats/>; rel="stats", '
            '<http://testserver/api/fields/{id}/>; rel="self", '
            '<http://testserver/api/fields/{id}/values/>; rel="values", '
            '<http://testserver/api/fields/{id}/dist/>; rel="distribution", '
            '<http://testserver/api/fields/{id}/dims/>; rel="dimensions"'
        ))

    def test_get_all_unrelated(self):
        # Publish unrelated field
        DataField.objects.filter(model_name='unrelated').update(published=True)

        # Should not appear in default request since it's not related
        response = self.client.get('/api/fields/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 5)

        # Switch the tree, now it should be the only one
        response = self.client.get('/api/fields/?tree=unrelated',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 1)

    def test_stats_capable_setting(self):
        f = DataField.objects.get_by_natural_key('tests', 'title', 'name')

        # Initially, the default stats_capable check will be used that allows
        # for stats on all non-searchable fields so we will expect that the
        # stats endpoint will return normally.
        response = self.client.get('/api/fields/{0}/'.format(f.pk),
                                   HTTP_ACCEPT='applicaton/json')
        content = json.loads(response.content)
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue('stats_capable' in content)

        response = self.client.get('/api/fields/{0}/stats/'.format(f.pk),
                                   HTTP_ACCEPT='applicaton/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(response['Link-Template'], (
            '<http://testserver/api/fields/{id}/stats/>; rel="self", '
            '<http://testserver/api/fields/{parent_id}/>; rel="parent"'
        ))

        # Now, overriding that setting so that this field is not
        # "stats_capable" should 'disable' the stats endpoint for that field.
        with self.settings(SERRANO_STATS_CAPABLE=lambda x: x.id != f.pk):
            response = self.client.get('/api/fields/{0}/'.format(f.pk),
                                       HTTP_ACCEPT='applicaton/json')
            content = json.loads(response.content)
            self.assertEqual(response.status_code, codes.ok)
            self.assertFalse('stats_capable' in content)

            response = self.client.get('/api/fields/{0}/stats/'.format(f.pk),
                                       HTTP_ACCEPT='applicaton/json')
            self.assertEqual(response.status_code, codes.unprocessable_entity)

    @override_settings(SERRANO_CHECK_ORPHANED_FIELDS=True)
    def test_get_all_orphan(self):
        f = DataField.objects.get_by_natural_key('tests', 'title', 'name')

        # Orphan one of the fields we are about to retrieve
        DataField.objects.filter(pk=f.pk).update(field_name="XXX")

        response = self.client.get('/api/fields/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 4)

    @override_settings(SERRANO_CHECK_ORPHANED_FIELDS=False)
    def test_get_all_orphan_check_off(self):
        f = DataField.objects.get_by_natural_key('tests', 'title', 'name')

        # Orphan one of the fields we are about to retrieve
        DataField.objects.filter(pk=f.pk).update(field_name="XXX")

        response = self.client.get('/api/fields/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 5)

    def test_get_one(self):
        f1 = DataField.objects.get_by_natural_key('tests',
                                                  'office',
                                                  'location')
        f2 = DataField.objects.get_by_natural_key('tests',
                                                  'title',
                                                  'name')

        # Not allowed to see
        response = self.client.get('/api/fields/{0}/'.format(f1.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)

        response = self.client.get('/api/fields/{0}/'.format(f2.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(json.loads(response.content))

        event = Log.objects.filter(event='read', object_id=f2.pk)
        self.assertTrue(event.exists())

    @override_settings(SERRANO_CHECK_ORPHANED_FIELDS=True)
    def test_get_one_orphan(self):
        f = DataField.objects.get_by_natural_key('tests',
                                                 'title',
                                                 'name')
        # Orphan the field before we retrieve it.
        # NOTE: Used to be model_name, but changed due to the tree
        # filtering removing it from the set.
        DataField.objects.filter(pk=f.pk).update(field_name="XXX")

        response = self.client.get('/api/fields/{0}/'.format(f.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.internal_server_error)

    @override_settings(SERRANO_CHECK_ORPHANED_FIELDS=False)
    def test_get_one_orphan_check_off(self):
        f = DataField.objects.get_by_natural_key('tests',
                                                 'title',
                                                 'name')

        # Orphan one of the fields we are about to retrieve
        DataField.objects.filter(pk=f.pk).update(field_name="XXX")

        response = self.client.get('/api/fields/{0}/'.format(f.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)

    def test_get_privileged(self):
        f1 = DataField.objects.get_by_natural_key('tests',
                                                  'office',
                                                  'location')

        # Superuser sees everything
        self.client.login(username='root', password='password')

        response = self.client.get('/api/fields/?unpublished=1',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 12)

        response = self.client.get('/api/fields/{0}/?unpublished=1'
                                   .format(f1.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(json.loads(response.content))

        # Make sure the unpublished fields are only exposed when explicitly
        # asked for even when a superuser makes the request.
        response = self.client.get('/api/fields/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 5)

        response = self.client.get('/api/fields/{0}/'.format(f1.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)

    def test_values(self):
        f2 = DataField.objects.get_by_natural_key('tests',
                                                  'title',
                                                  'name')
        # title.name
        response = self.client.get('/api/fields/{0}/values/'.format(f2.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        content = json.loads(response.content)
        self.assertTrue(content['items'])
        self.assertTrue(len(content['items']), 7)

        response = self.client.get(
            '/api/fields/{0}/values/?processor=first_title'.format(f2.pk),
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        content = json.loads(response.content)
        self.assertTrue(content['items'])
        self.assertTrue(len(content['items']), 1)

    def test_values_no_limit(self):
        f2 = DataField.objects.get_by_natural_key('tests',
                                                  'title',
                                                  'name')

        # title.name
        response = self.client.get('/api/fields/{0}/values/?limit=0'
                                   .format(f2.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        data = json.loads(response.content)
        self.assertTrue(data['items'])
        self.assertFalse('previous' in response['Link'])
        self.assertFalse('next' in response['Link'])
        self.assertTrue('parent' in response['Link-Template'])
        self.assertTrue(
            'self' in response['Link'] and 'base' in response['Link'])

    def test_zero_division_error(self):
        f2 = DataField.objects.get_by_natural_key('tests',
                                                  'title',
                                                  'name')
        # Delete everything for now
        Title.objects.all().delete()

        response = self.client.get('/api/fields/{0}/values/?limit=0'
                                   .format(f2.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        data = json.loads(response.content)
        self.assertEqual(data['items'], [])

    def test_values_random(self):
        f2 = DataField.objects.get_by_natural_key('tests',
                                                  'title',
                                                  'name')
        # Random values
        response = self.client.get('/api/fields/{0}/values/?random=3'
                                   .format(f2.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 3)

        # Even though we are requesting 3 values, the query processor should
        # limit the population to 1 value so make sure that the call returns
        # only that single value since all values in the population should be
        # returned when the random sample size is bigger than population size.
        response = self.client.get(
            '/api/fields/{0}/values/?random=3&processor=first_title'
            .format(f2.pk),
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 1)

    def test_values_query(self):
        f2 = DataField.objects.get_by_natural_key('tests',
                                                  'title',
                                                  'name')

        response = self.client.get('/api/fields/{0}/values/?query=a'
                                   .format(f2.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(json.loads(response.content)['items'], [
            {'label': 'Analyst', 'value': 'Analyst'},
            {'label': 'Guard', 'value': 'Guard'},
            {'label': 'Lawyer', 'value': 'Lawyer'},
            {'label': 'Programmer', 'value': 'Programmer'},
            {'label': 'QA', 'value': 'QA'},
        ])
        message = Log.objects.get(event='items', object_id=f2.pk)
        self.assertEqual(message.data['query'], 'a')

        response = self.client.get(
            '/api/fields/{0}/values/?query=a&processor=under_twenty_thousand'
            .format(f2.pk),
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(json.loads(response.content)['items'], [
            {'label': 'Guard', 'value': 'Guard'},
            {'label': 'Programmer', 'value': 'Programmer'},
            {'label': 'QA', 'value': 'QA'},
        ])

    def test_values_validate(self):
        f2 = DataField.objects.get_by_natural_key('tests',
                                                  'title',
                                                  'name')
        # Valid, single dict
        response = self.client.post(
            '/api/fields/{0}/values/'.format(f2.pk),
            data=json.dumps({'value': 'IT'}),
            content_type='application/json',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        content = json.loads(response.content)
        self.assertEqual(content, {
            'value': 'IT',
            'label': 'IT',
            'valid': True,
        })
        message = Log.objects.get(event='validate', object_id=f2.pk)
        self.assertEqual(message.data['count'], 1)

        # Invalid
        response = self.client.post(
            '/api/fields/{0}/values/'.format(f2.pk),
            data=json.dumps({'value': 'Bartender'}),
            content_type='application/json',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        content = json.loads(response.content)
        self.assertEqual(content, {
            'value': 'Bartender',
            'label': 'Bartender',
            'valid': False,
        })

        # Mixed, list
        response = self.client.post(
            '/api/fields/{0}/values/'.format(f2.pk),
            data=json.dumps([
                {'value': 'IT'},
                {'value': 'Bartender'},
                {'value': 'Programmer'}
            ]),
            content_type='application/json',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        content = json.loads(response.content)
        self.assertEqual(content, [
            {'value': 'IT', 'label': 'IT', 'valid': True},
            {'value': 'Bartender', 'label': 'Bartender', 'valid': False},
            {'value': 'Programmer', 'label': 'Programmer', 'valid': True},
        ])

        # Error - no value
        response = self.client.post(
            '/api/fields/{0}/values/'.format(f2.pk),
            data=json.dumps({}),
            content_type='application/json',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.unprocessable_entity)

        # Error - type
        response = self.client.post(
            '/api/fields/{0}/values/'.format(f2.pk),
            data=json.dumps(None),
            content_type='application/json',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.unprocessable_entity)

    def test_labels_validate(self):
        f2 = DataField.objects.get_by_natural_key('tests',
                                                  'title',
                                                  'name')
        # Valid, single dict
        response = self.client.post(
            '/api/fields/{0}/values/'.format(f2.pk),
            data=json.dumps({'label': 'IT'}),
            content_type='application/json',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        content = json.loads(response.content)
        self.assertEqual(content, {
            'value': 'IT',
            'label': 'IT',
            'valid': True,
        })

    def test_mixed_validate(self):
        f2 = DataField.objects.get_by_natural_key('tests',
                                                  'title',
                                                  'name')
        response = self.client.post(
            '/api/fields/{0}/values/'.format(f2.pk),
            data=json.dumps([
                {'label': 'IT'},
                {'label': 'Bartender'},
                {'value': 'Programmer'}
            ]),
            content_type='application/json',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        content = json.loads(response.content)
        self.assertEqual(content, [
            {'value': 'IT', 'label': 'IT', 'valid': True},
            {'value': 'Bartender', 'label': 'Bartender', 'valid': False},
            {'value': 'Programmer', 'label': 'Programmer', 'valid': True},
        ])

    def test_stats(self):
        f2 = DataField.objects.get_by_natural_key('tests',
                                                  'title',
                                                  'name')

        f3 = DataField.objects.get_by_natural_key('tests',
                                                  'title',
                                                  'salary')
        # title.name
        response = self.client.get('/api/fields/{0}/stats/'.format(f2.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(json.loads(response.content))
        self.assertTrue(
            Log.objects.filter(event='stats', object_id=f2.pk).exists())

        # title.salary
        response = self.client.get('/api/fields/{0}/stats/'.format(f3.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        stats = json.loads(response.content)
        self.assertTrue(stats)
        self.assertTrue(
            Log.objects.filter(event='stats', object_id=f3.pk).exists())
        self.assertEqual(stats['min'], 10000)
        self.assertEqual(stats['max'], 200000)
        self.assertAlmostEqual(stats['avg'], 53571.42857, places=5)

        # Using an invalid query processor should fall back to the default.
        response = self.client.get('/api/fields/{0}/stats/?processor=INVALID'
                                   .format(f3.pk),
                                   HTTP_ACCEPT='application/json')
        stats = json.loads(response.content)
        self.assertEqual(stats['min'], 10000)
        self.assertEqual(stats['max'], 200000)
        self.assertAlmostEqual(stats['avg'], 53571.42857, places=5)

        # Using a valid query processor should affect the stats.
        response = self.client.get(
            '/api/fields/{0}/stats/?processor=under_twenty_thousand'
            .format(f3.pk),
            HTTP_ACCEPT='application/json')
        stats = json.loads(response.content)
        self.assertEqual(stats['min'], 10000)
        self.assertEqual(stats['max'], 15000)
        self.assertEqual(stats['avg'], 13750)

        # project.due_date
        f11 = DataField.objects.get_by_natural_key('tests',
                                                   'project',
                                                   'due_date')
        response = self.client.get('/api/fields/{0}/stats/'.format(f11.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)

        stats = json.loads(response.content)

        self.assertTrue(stats)
        self.assertTrue(
            Log.objects.filter(event='stats', object_id=f11.pk).exists())
        self.assertEqual(stats['min'], '2000-01-01')
        self.assertEqual(stats['max'], '2010-01-01')

    def test_empty_stats(self):
        f2 = DataField.objects.get_by_natural_key('tests',
                                                  'title',
                                                  'name')
        Title.objects.all().delete()

        response = self.client.get('/api/fields/{0}/stats/'.format(f2.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(json.loads(response.content))
        self.assertTrue(
            Log.objects.filter(event='stats', object_id=f2.pk).exists())

    def test_dist(self):
        f3 = DataField.objects.get_by_natural_key('tests',
                                                  'title',
                                                  'salary')

        default_content = [
            {'label': '10000', 'value': 10000, 'count': 1},
            {'label': '15000', 'value': 15000, 'count': 3},
            {'label': '20000', 'value': 20000, 'count': 1},
            {'label': '100000', 'value': 100000, 'count': 1},
            {'label': '200000', 'value': 200000, 'count': 1},
        ]

        # title.salary
        response = self.client.get('/api/fields/{0}/dist/'.format(f3.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(json.loads(response.content), default_content)

        event = Log.objects.filter(event='dist', object_id=f3.pk)
        self.assertTrue(event.exists())

        # Using an invalid processor should fallback to the default processor.
        response = self.client.get('/api/fields/{0}/dist/?processor=INVALID'
                                   .format(f3.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(json.loads(response.content), default_content)

        # Using the custom query process, we should be limited to a smaller
        # salary set.
        response = self.client.get('/api/fields/{0}/dist/?processor=manager'
                                   .format(f3.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(json.loads(response.content), [
            {'label': '15000', 'value': 15000, 'count': 1},
        ])

    def test_dims(self):
        f3 = DataField.objects.get_by_natural_key('tests',
                                                  'title',
                                                  'salary')

        default_content = {
            u'size': 4,
            u'clustered': False,
            u'outliers': [],
            u'data': [{
                u'count': 3,
                u'values': [{'label': '15000', 'value': 15000}]
            }, {
                u'count': 1,
                u'values': [{'label': '10000', 'value': 10000}]
            }, {
                u'count': 1,
                u'values': [{'label': '20000', 'value': 20000}]
            }, {
                u'count': 1,
                u'values': [{'label': '200000', 'value': 200000}]
            }],
        }

        # title.salary
        response = self.client.get('/api/fields/{0}/dims/'.format(f3.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(json.loads(response.content), default_content)

        event = Log.objects.filter(event='dims', object_id=f3.pk)
        self.assertTrue(event.exists())

        # Using an invalid processor should fallback to the default processor.
        response = self.client.get('/api/fields/{0}/dims/?processor=INVALID'
                                   .format(f3.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(json.loads(response.content), default_content)

        # Using the custom query process, we should be limited to a smaller
        # salary set.
        response = self.client.get('/api/fields/{0}/dims/?processor=manager'
                                   .format(f3.pk),
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(json.loads(response.content), {
            u'size': 1,
            u'clustered': False,
            u'outliers': [],
            u'data': [{
                u'count': 1,
                u'values': [{'label': '15000', 'value': 15000}]
            }]
        })
