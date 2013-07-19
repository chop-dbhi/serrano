import json
import time
from django.conf import settings
from django.contrib.auth.models import User
from django.core import management
from django.core.cache import cache
from django.test import TestCase
from django.test.utils import override_settings
from avocado.conf import OPTIONAL_DEPS
from avocado.models import DataField, DataConcept, DataConceptField, \
    DataContext, DataView, DataQuery, Log
from restlib2.http import codes
from serrano.resources import API_VERSION

class BaseTestCase(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        management.call_command('avocado', 'init', 'tests', quiet=True)
        # Only publish some of them..
        DataField.objects.filter(model_name='title').update(published=True)
        self.user = User.objects.create_user(username='root',
            password='password')
        self.user.is_superuser = True
        self.user.save()


class RootResourceTestCase(TestCase):
    def test_get(self):
        response = self.client.get('/api/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(json.loads(response.content), {
            'title': 'Serrano Hypermedia API',
            'version': API_VERSION,
            '_links': {
                'exporter': {'href': 'http://testserver/api/data/export/'},
                'views': {'href': 'http://testserver/api/views/'},
                'contexts': {'href': 'http://testserver/api/contexts/'},
                'queries': {'href': 'http://testserver/api/queries/'},
                'fields': {'href': 'http://testserver/api/fields/'},
                'self': {'href': 'http://testserver/api/'},
                'concepts': {'href': 'http://testserver/api/concepts/'},
                'preview': {'href': 'http://testserver/api/data/preview/'},
            },
        })

    @override_settings(SERRANO_AUTH_REQUIRED=True)
    def test_post(self):
        User.objects.create_user(username='root', password='password')
        response = self.client.post('/api/',
            content_type='application/json',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.content, 'Invalid credentials')

        response = self.client.post('/api/',
            json.dumps({'username': 'root', 'password': 'password'}),
            content_type='application/json',
            HTTP_ACCEPT='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue('token' in json.loads(response.content))


class PreviewResourceTestCase(TestCase):
    def test_get(self):
        response = self.client.get('/api/data/preview/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(json.loads(response.content), {
            '_links': {
                'self': {
                    'href': 'http://testserver/api/data/preview/?limit=20&page=1',
                },
                'base': {
                    'href': 'http://testserver/api/data/preview/',
                }
            },
            'keys': [],
            'object_count': 0,
            'object_name': 'employee',
            'object_name_plural': 'employees',
            'objects': [],
            'page_num': 1,
            'num_pages': 1,
            'limit': 20,
        })


class ExporterResourceTestCase(TestCase):
    def test_get(self):
        response = self.client.get('/api/data/export/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

        expectedResponse = {
            'title': 'Serrano Exporter Endpoints',
            'version': API_VERSION,
            '_links': {
                'self': {'href': 'http://testserver/api/data/export/'},
                'json': {
                    'href': 'http://testserver/api/data/export/json/',
                    'description': 'JavaScript Object Notation (JSON)',
                    'title': 'JSON'
                },
                'r': {
                    'href': 'http://testserver/api/data/export/r/',
                    'description': 'R Programming Language',
                    'title': 'R'
                },
                'sas': {
                    'href': 'http://testserver/api/data/export/sas/',
                    'description': 'Statistical Analysis System (SAS)',
                    'title': 'SAS'
                },
                'csv': {
                    'href': 'http://testserver/api/data/export/csv/',
                    'description': 'Comma-Separated Values (CSV)',
                    'title': 'CSV'
                }
            },
        }

        if OPTIONAL_DEPS['openpyxl']:
            expectedResponse['_links']['excel'] = {
                'href': 'http://testserver/api/data/export/excel/',
                'description': 'Microsoft Excel 2007 Format',
                'title': 'Excel'
            }

        self.assertEqual(json.loads(response.content), expectedResponse)


@override_settings(SERRANO_RATE_LIMIT_COUNT=None)
class DataResourceTestCase(BaseTestCase):
    def test_too_many_auth_requests(self):
        self.client.login(username='root', password='password')

        # Be certain we are clear of the current interval
        time.sleep(7)

        # These 20 requests should be OK
        for _ in range(20):
            response = self.client.get('/api/fields/2/',
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 200)

        # Wait a little while but stay in the interval
        time.sleep(3)

        # These 20 requests should be still be OK
        for _ in range(20):
            response = self.client.get('/api/fields/2/',
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 200)

        # These 10 requests should fail as we've exceeded the limit
        for _ in range(10):
            response = self.client.get('/api/fields/2/',
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, codes.too_many_requests)

        # Wait out the interval
        time.sleep(6)

        # These 5 requests should be OK
        for _ in range(5):
            response = self.client.get('/api/fields/2/',
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 200)


    def test_too_many_requests(self):
        # Force these the requests to be unauthenitcated
        self.user = None

        # We execute a request before the actual test in order to initialize
        # the session so that we have valid session keys on subsequent
        # requests.
        # TODO: Can the session be initialized somehow without sending
        # a request via the client?
        response = self.client.get('/api/fields/2/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)

        # Be certain we are clear of the current interval
        time.sleep(5)

        # These 10 requests should be OK
        for _ in range(10):
            response = self.client.get('/api/fields/2/',
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 200)

        # Wait a little while but stay in the interval
        time.sleep(1)

        # These 10 requests should be still be OK
        for _ in range(10):
            response = self.client.get('/api/fields/2/',
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 200)

        # These 10 requests should fail as we've exceeded the limit
        for _ in range(10):
            response = self.client.get('/api/fields/2/',
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, codes.too_many_requests)

        # Wait out the interval
        time.sleep(4)

        # These 5 requests should be OK
        for _ in range(5):
            response = self.client.get('/api/fields/2/',
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 200)


class FieldResourceTestCase(BaseTestCase):
    def test_get_all(self):
        response = self.client.get('/api/fields/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 3)

    def test_get_all_orphan(self):
        # Orphan one of the fields we are about to retrieve
        DataField.objects.filter(pk=2).update(field_name="XXX")

        response = self.client.get('/api/fields/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 2)

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
        self.assertTrue(json.loads(response.content))
        self.assertTrue(Log.objects.filter(event='stats', object_id=3).exists())

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


class ConceptResourceTestCase(BaseTestCase):
    def setUp(self):
        super(ConceptResourceTestCase, self).setUp()

        name_field = DataField.objects.get_by_natural_key('tests', 'title',
                        'name')
        salary_field = DataField.objects.get_by_natural_key('tests', 'title',
                        'salary')
        boss_field = DataField.objects.get_by_natural_key('tests', 'title',
                        'boss')

        c1 = DataConcept(name='Title', published=True, pk=1)
        c1.save()
        DataConceptField(concept=c1, field=name_field, order=1).save()
        DataConceptField(concept=c1, field=salary_field, order=2).save()
        DataConceptField(concept=c1, field=boss_field, order=3).save()

        c2 = DataConcept(name='Salary', pk=2)
        c2.save()
        DataConceptField(concept=c2, field=salary_field, order=1).save()
        DataConceptField(concept=c2, field=boss_field, order=2).save()

        c3 = DataConcept(name='Name', published=True, pk=3)
        c3.save()
        DataConceptField(concept=c1, field=name_field, order=1).save()

    def test_get_all(self):
        response = self.client.get('/api/concepts/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 2)

    def test_get_all_orphan(self):
        # Orphan one of the fields we are about to embed in the concepts we
        # are about to retrieve.
        DataField.objects.filter(pk=2).update(field_name='XXX')

        response = self.client.get('/api/concepts/', {'embed': True},
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 1)

        # If we aren't embedding the fields, then we none of the concepts 
        # should be filtered out.
        response = self.client.get('/api/concepts/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 2)

    def test_get_one(self):
        response = self.client.get('/api/concepts/999/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 404)

        response = self.client.get('/api/concepts/3/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content))
        self.assertTrue(Log.objects.filter(event='read', object_id=3).exists())

    def test_get_one_orphan(self):
        # Orphan one of the fields on the concept before we retrieve it
        DataField.objects.filter(pk=2).update(model_name="XXX")

        response = self.client.get('/api/concepts/1/', {'embed': True},
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 500)

        # If we aren't embedding the fields, there should not be a server error
        response = self.client.get('/api/concepts/1/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)



class ConceptFieldResourceTestCase(BaseTestCase):
    def setUp(self):
        super(ConceptFieldResourceTestCase, self).setUp()

        name_field = DataField.objects.get_by_natural_key('tests', 'title',
                        'name')
        salary_field = DataField.objects.get_by_natural_key('tests', 'title',
                        'salary')
        boss_field = DataField.objects.get_by_natural_key('tests', 'title',
                        'boss')

        c1 = DataConcept(name='Title', published=True, pk=1)
        c1.save()
        DataConceptField(concept=c1, field=name_field, order=1).save()
        DataConceptField(concept=c1, field=salary_field, order=2).save()
        DataConceptField(concept=c1, field=boss_field, order=3).save()

    def test_get(self):
        response = self.client.get('/api/concepts/1/fields/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 3)

    def test_get_orphan(self):
        # Orphan the data field linked to the concept we are about to read 
        # the fields for.
        DataField.objects.filter(pk=2).update(field_name="XXX")

        response = self.client.get('/api/concepts/1/fields/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 500)

class ContextResourceTestCase(BaseTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test', password='test')
        self.client.login(username='test', password='test')

    def test_get_all(self):
        response = self.client.get('/api/contexts/',
            HTTP_ACCEPT='application/json')
        self.assertFalse(json.loads(response.content))

    def test_get_all_default(self):
        cxt = DataContext(template=True, default=True, json={})
        cxt.save()
        response = self.client.get('/api/contexts/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 1)

    def test_get(self):
        ctx = DataContext(user=self.user)
        ctx.save()
        response = self.client.get('/api/contexts/1/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content)
        self.assertLess(ctx.accessed,
                DataContext.objects.get(pk=ctx.pk).accessed)


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


class QueryResourceTestCase(BaseTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test', password='test')
        self.client.login(username='test', password='test')

    def test_get_all(self):
        response = self.client.get('/api/queries/',
            HTTP_ACCEPT='application/json')
        self.assertFalse(json.loads(response.content))

    def test_get_all_default(self):
        query = DataQuery(template=True, default=True, json={})
        query.save()
        response = self.client.get('/api/queries/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 1)

    def test_get(self):
        query = DataQuery(user=self.user)
        query.save()
        response = self.client.get('/api/queries/1/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content)
        self.assertLess(query.accessed,
                DataQuery.objects.get(pk=query.pk).accessed)

    def test_shared_user(self):
        query = DataQuery(user=self.user)
        query.save()
        sharee = User(username='sharee', first_name='Shared',
            last_name='User', email='share@example.com')
        sharee.save()
        query.shared_users.add(sharee)
        response = self.client.get('/api/queries/1/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(json.loads(response.content)['shared_users'][0], {
            'id': 2,
            'username': 'sharee',
            'name': 'Shared User',
            'email': 'share@example.com',
        })
