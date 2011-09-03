from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils import simplejson

__all__ = ('SessionReportResourceTestCase', 'ReportResourceTestCase')

class SessionReportResourceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('foo', 'foo@bar.com', 'bar')
        self.client.login(username='foo', password='bar')

    def test_get(self):
        response = self.client.get(reverse('api:reports:session'), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(simplejson.loads(response.content)['name'], None)

    def test_put(self):
        json = simplejson.dumps({'name': 'A Report'})
        response = self.client.put(reverse('api:reports:session'), json, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(simplejson.loads(response.content)['name'], 'A Report')
        self.assertFalse(self.client.session['report'].has_changed())


class ReportResourceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('foo', 'foo@bar.com', 'bar')
        self.client.login(username='foo', password='bar')

        from avocado.store.models import Report, Scope, Perspective
        scope = Scope()
        scope.save()
        perspective = Perspective()
        perspective.save()

        self.report = Report(name='Some Report', scope=scope, perspective=perspective, user=self.user)
        self.report.save()

    def test_get(self):
        response = self.client.get(reverse('api:reports:read', args=[self.report.pk]), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.report, self.client.session['report'].reference)

        # subsequent request
        response = self.client.get(reverse('api:reports:read', args=[self.report.pk]), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.report, self.client.session['report'].reference)

    def test_put_with_reference(self):
        response = self.client.get(reverse('api:reports:read', args=[self.report.pk]), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        json = simplejson.dumps({'name': 'Renamed Report'})
        response = self.client.put(reverse('api:reports:read', args=[self.report.pk]), json, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(simplejson.loads(response.content)['name'], 'Renamed Report')
        self.assertEqual(simplejson.loads(response.content)['id'], self.report.pk)

    def test_put_without_reference(self):
        json = simplejson.dumps({'name': 'Another Renamed Report'})

        response = self.client.put(reverse('api:reports:read', args=[self.report.pk]), json, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(simplejson.loads(response.content)['name'], 'Another Renamed Report')
        self.assertEqual(simplejson.loads(response.content)['id'], self.report.pk)

    def test_delete_with_reference(self):
        response = self.client.get(reverse('api:reports:read', args=[self.report.pk]), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)

        response = self.client.delete(reverse('api:reports:read', args=[self.report.pk]), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.session['report'].reference, None)

    def test_delete_without_reference(self):
        response = self.client.delete(reverse('api:reports:read', args=[self.report.pk]), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.session['report'].reference, None)
