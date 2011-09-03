from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils import simplejson

__all__ = ('SessionScopeResourceTestCase', 'ScopeResourceTestCase')

class SessionScopeResourceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('foo', 'foo@bar.com', 'bar')
        self.client.login(username='foo', password='bar')

    def test_get(self):
        response = self.client.get(reverse('api:scope:session'), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(simplejson.loads(response.content)['store'], None)

    def test_put(self):
        json = simplejson.dumps({'name': 'A Scope'})
        response = self.client.put(reverse('api:scope:session'), json, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(simplejson.loads(response.content)['name'], 'A Scope')

        json = simplejson.dumps({'store': {}})
        response = self.client.put(reverse('api:scope:session'), json, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(simplejson.loads(response.content)['store'], {})

class ScopeResourceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('foo', 'foo@bar.com', 'bar')
        self.client.login(username='foo', password='bar')

        from avocado.store.models import Scope
        self.scope = Scope(name='Some Scope', user=self.user)
        self.scope.save()

    def test_get(self):
        response = self.client.get(reverse('api:scope:read', args=[self.scope.pk]), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.scope, self.client.session['report'].scope.reference)

        # subsequent request
        response = self.client.get(reverse('api:scope:read', args=[self.scope.pk]), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.scope, self.client.session['report'].scope.reference)

    def test_put_with_reference(self):
        response = self.client.get(reverse('api:scope:read', args=[self.scope.pk]), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        json = simplejson.dumps({'name': 'Renamed Scope'})
        response = self.client.put(reverse('api:scope:read', args=[self.scope.pk]), json, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(simplejson.loads(response.content)['name'], 'Renamed Scope')
        self.assertEqual(simplejson.loads(response.content)['id'], self.scope.pk)

    def test_put_without_reference(self):
        json = simplejson.dumps({'name': 'Another Renamed Scope'})
        response = self.client.put(reverse('api:scope:read', args=[self.scope.pk]), json, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(simplejson.loads(response.content)['name'], 'Another Renamed Scope')
        self.assertEqual(simplejson.loads(response.content)['id'], self.scope.pk)

    def test_delete_with_reference(self):
        response = self.client.get(reverse('api:scope:read', args=[self.scope.pk]), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        response = self.client.delete(reverse('api:scope:read', args=[self.scope.pk]), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.session['report'].scope.reference, None)

    def test_delete_without_reference(self):
        response = self.client.delete(reverse('api:scope:read', args=[self.scope.pk]), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.session['report'].scope.reference, None)
