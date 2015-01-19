import json
from django.test.utils import override_settings
from restlib2.http import codes
from avocado.models import DataConcept, DataConceptField, DataField, \
    DataCategory
from avocado.events.models import Log
from .base import BaseTestCase


class ConceptResourceTestCase(BaseTestCase):
    def setUp(self):
        super(ConceptResourceTestCase, self).setUp()

        self.name_field = DataField.objects.get_by_natural_key(
            'tests', 'title', 'name')
        self.salary_field = DataField.objects.get_by_natural_key(
            'tests', 'title', 'salary')
        self.boss_field = DataField.objects.get_by_natural_key(
            'tests', 'title', 'boss')

        c1 = DataConcept(name='Title', published=True)
        c1.save()
        DataConceptField(concept=c1, field=self.name_field, order=1).save()
        DataConceptField(concept=c1, field=self.salary_field, order=2).save()
        DataConceptField(concept=c1, field=self.boss_field, order=3).save()

        c2 = DataConcept(name='Salary')
        c2.save()
        DataConceptField(concept=c2, field=self.salary_field, order=1).save()
        DataConceptField(concept=c2, field=self.boss_field, order=2).save()

        c3 = DataConcept(name='Name', published=True)
        c3.save()
        DataConceptField(concept=c3, field=self.name_field, order=1).save()

    def test_get_all(self):
        response = self.client.get('/api/concepts/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 2)

        self.assertEqual(response['Link-Template'], (
            '<http://testserver/api/concepts/{id}/>; rel="self"'
        ))

    def test_get_all_unrelated(self):
        # Publish unrelated field and concept
        f = DataField.objects.get(model_name='unrelated')
        f.published = True
        f.save()

        c = DataConcept(name='Unrelated', published=True)
        c.save()

        DataConceptField(concept=c, field=f, order=1).save()

        # Concept from two unrelated fields.. this will never show.
        # TODO don't allow this
        c = DataConcept(name='Unrelated', published=True)
        c.save()

        DataConceptField(concept=c, field=f, order=1).save()
        DataConceptField(concept=c, field=self.boss_field, order=2).save()

        # Still 2 concepts visible by default tree
        response = self.client.get('/api/concepts/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 2)

        # 1 concept visible for unrelated tree
        response = self.client.get('/api/concepts/?tree=unrelated',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 1)

    def test_get_all_category_sort(self):
        # Create some temporary concepts and categories.
        cat1 = DataCategory(name='Category1', order=1.0, published=True)
        cat1.save()

        c1 = DataConcept(name='B', published=True, category=cat1)
        c1.save()
        field1 = DataConceptField(concept=c1, field=self.name_field, order=1)
        field1.save()

        c2 = DataConcept(name='C', published=True, category=cat1)
        c2.save()
        field2 = DataConceptField(concept=c2, field=self.name_field, order=1)
        field2.save()

        c3 = DataConcept(name='A', published=True, category=cat1)
        c3.save()
        field3 = DataConceptField(concept=c3, field=self.name_field, order=1)
        field3.save()

        # Check that category ordering is happening by default.
        response = self.client.get('/api/concepts/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 5)
        names = [concept.get('name', '') for concept in
                 json.loads(response.content)]
        self.assertEqual(names, ['Title', 'Name', 'B', 'C', 'A'])

        # Reverse the ordering of the categories.
        response = self.client.get('/api/concepts/',
                                   {'order': 'desc'},
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 5)
        names = [concept.get('name', '') for concept in
                 json.loads(response.content)]
        self.assertEqual(names, ['B', 'C', 'A', 'Title', 'Name'])

        # Order by concept name in addition to category.
        response = self.client.get('/api/concepts/',
                                   {'sort': 'name'},
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 5)
        names = [concept.get('name', '') for concept in
                 json.loads(response.content)]
        self.assertEqual(names, ['Name', 'Title', 'A', 'B', 'C'])

        # Reverse the name and category sorting.
        response = self.client.get('/api/concepts/',
                                   {'sort': 'name', 'order': 'desc'},
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 5)
        names = [concept.get('name', '') for concept in
                 json.loads(response.content)]
        self.assertEqual(names, ['C', 'B', 'A', 'Title', 'Name'])

        c1.delete()
        c2.delete()
        c3.delete()
        field1.delete()
        field2.delete()
        field3.delete()
        cat1.delete()

    def test_get_all_name_sort(self):
        response = self.client.get('/api/concepts/',
                                   {'sort': 'name'},
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 2)
        names = [concept.get('name', '') for concept in
                 json.loads(response.content)]
        self.assertEqual(names, ['Name', 'Title'])

        response = self.client.get('/api/concepts/',
                                   {'sort': 'name', 'order': 'desc'},
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 2)
        names = [concept.get('name', '') for concept in
                 json.loads(response.content)]
        self.assertEqual(names, ['Title', 'Name'])

    def test_get_all_limit(self):
        # Name and title are both published but with the limit param set below
        # we should only get one back.
        response = self.client.get('/api/concepts/',
                                   {'limit': 1},
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 1)

    @override_settings(SERRANO_CHECK_ORPHANED_FIELDS=True)
    def test_get_all_orphan(self):
        # Orphan one of the fields of the concepts we are about to retrieve.
        DataField.objects.filter(pk=self.salary_field.pk) \
            .update(field_name='XXX')

        with self.settings(SERRANO_CHECK_ORPHANED_FIELDS=True):
            response = self.client.get('/api/concepts/',
                                       HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, codes.ok)
            self.assertEqual(len(json.loads(response.content)), 1)

        with self.settings(SERRANO_CHECK_ORPHANED_FIELDS=False):
            response = self.client.get('/api/concepts/',
                                       HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, codes.ok)
            self.assertEqual(len(json.loads(response.content)), 2)

    def test_get_one(self):
        response = self.client.get('/api/concepts/999/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)

        response = self.client.get('/api/concepts/3/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(json.loads(response.content))
        self.assertTrue(Log.objects.filter(event='read', object_id=3).exists())

    @override_settings(SERRANO_CHECK_ORPHANED_FIELDS=True)
    def test_get_one_orphan(self):
        # Orphan one of the fields on the concept before we retrieve it.
        DataField.objects.filter(pk=self.salary_field.pk) \
            .update(field_name='XXX')

        with self.settings(SERRANO_CHECK_ORPHANED_FIELDS=True):
            response = self.client.get('/api/concepts/1/',
                                       HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, codes.internal_server_error)

        with self.settings(SERRANO_CHECK_ORPHANED_FIELDS=False):
            response = self.client.get('/api/concepts/1/',
                                       HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, codes.ok)

    def test_search(self):
        response = self.client.get('/api/concepts/?query=XYZ',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 0)

        response = self.client.get('/api/concepts/?query=itle',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertEqual(len(json.loads(response.content)), 1)

        # Orphan one of the fields on the concept we are searching for.
        DataField.objects.filter(pk=self.name_field.pk) \
            .update(field_name='XXX')

        with self.settings(SERRANO_CHECK_ORPHANED_FIELDS=True):
            response = self.client.get('/api/concepts/?query=itle',
                                       HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, codes.ok)
            self.assertEqual(len(json.loads(response.content)), 0)

        with self.settings(SERRANO_CHECK_ORPHANED_FIELDS=False):
            response = self.client.get('/api/concepts/?query=itle',
                                       HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, codes.ok)
            self.assertEqual(len(json.loads(response.content)), 1)

    def test_get_privileged(self):
        # Superuser sees everything
        self.client.login(username='root', password='password')

        response = self.client.get('/api/concepts/?unpublished=1',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 3)

        response = self.client.get('/api/concepts/2/?unpublished=1',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.ok)
        self.assertTrue(json.loads(response.content))

        # Make sure the unpublished concepts are only exposed when explicitly
        # asked for even when a superuser makes the request.
        response = self.client.get('/api/concepts/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 2)

        response = self.client.get('/api/concepts/2/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, codes.not_found)
