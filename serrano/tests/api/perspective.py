from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils import simplejson

__all__ = ('SessionPerspectiveResourceTestCase', 'PerspectiveResourceTestCase')

class SessionPerspectiveResourceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('foo', 'foo@bar.com', 'bar')
        self.client.login(username='foo', password='bar')

    def test_get(self):
        response = self.client.get(reverse('api:perspectives:session'), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(simplejson.loads(response.content)['store'], None)

    def test_put(self):
        json = simplejson.dumps({'name': 'A Perspective'})
        response = self.client.put(reverse('api:perspectives:session'), json, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(simplejson.loads(response.content)['name'], 'A Perspective')


class PerspectiveResourceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('foo', 'foo@bar.com', 'bar')
        self.client.login(username='foo', password='bar')

        from avocado.store.models import Perspective
        self.perspective = Perspective(name='Some Perspective', user=self.user)
        self.perspective.save()

    def test_get(self):
        response = self.client.get(reverse('api:perspectives:read', args=[self.perspective.pk]), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.perspective, self.client.session['report'].perspective.reference)

        # subsequent request
        response = self.client.get(reverse('api:perspectives:read', args=[self.perspective.pk]), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.perspective, self.client.session['report'].perspective.reference)

    def test_put_with_reference(self):
        response = self.client.get(reverse('api:perspectives:read', args=[self.perspective.pk]), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        json = simplejson.dumps({'name': 'Renamed Perspective'})

        response = self.client.put(reverse('api:perspectives:read', args=[self.perspective.pk]), json, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(simplejson.loads(response.content)['name'], 'Renamed Perspective')
        self.assertEqual(simplejson.loads(response.content)['id'], self.perspective.pk)

    def test_put_without_reference(self):
        json = simplejson.dumps({'name': 'Another Renamed Perspective'})

        response = self.client.put(reverse('api:perspectives:read', args=[self.perspective.pk]), json, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(simplejson.loads(response.content)['name'], 'Another Renamed Perspective')
        self.assertEqual(simplejson.loads(response.content)['id'], self.perspective.pk)

    def test_delete_with_reference(self):
        response = self.client.get(reverse('api:perspectives:read', args=[self.perspective.pk]), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)

        response = self.client.delete(reverse('api:perspectives:read', args=[self.perspective.pk]), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.session['report'].perspective.reference, None)

    def test_delete_without_reference(self):
        response = self.client.delete(reverse('api:perspectives:read', args=[self.perspective.pk]), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.session['report'].perspective.reference, None)
