import json
from django.test.utils import override_settings
from avocado.models import DataConcept, DataConceptField, DataField, Log
from .base import BaseTestCase


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

        # If we aren't embedding the fields, then none of the concepts
        # should be filtered out.
        response = self.client.get('/api/concepts/',
            HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)), 2)

    @override_settings(SERRANO_CHECK_ORPHANED_FIELDS=False)
    def test_get_all_orphan_check_off(self):
        # Orphan one of the fields we are about to embed in the concepts we
        # are about to retrieve.
        DataField.objects.filter(pk=2).update(field_name='XXX')

        self.assertRaises(AttributeError, self.client.get, '/api/concepts/',
            {'embed': True}, HTTP_ACCEPT='application/json')

        # If we aren't embedding the fields, then none of the concepts
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

    @override_settings(SERRANO_CHECK_ORPHANED_FIELDS=False)
    def test_get_one_orphan_check_off(self):
        # Orphan one of the fields on the concept before we retrieve it
        DataField.objects.filter(pk=2).update(model_name="XXX")

        self.assertRaises(AttributeError, self.client.get, '/api/concepts/1/',
            {'embed': True}, HTTP_ACCEPT='application/json')

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

    @override_settings(SERRANO_CHECK_ORPHANED_FIELDS=False)
    def test_get_orphan_check_off(self):
        # Orphan the data field linked to the concept we are about to read
        # the fields for.
        DataField.objects.filter(pk=2).update(field_name="XXX")

        self.assertRaises(AttributeError, self.client.get,
            '/api/concepts/1/fields/', HTTP_ACCEPT='application/json')
