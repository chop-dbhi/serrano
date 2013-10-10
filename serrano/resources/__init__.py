from django.http import HttpResponse
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from django.contrib.auth import authenticate, login
import serrano
from serrano.tokens import token_generator
from .base import BaseResource

API_VERSION = '{major}.{minor}.{micro}'.format(**serrano.__version_info__)


class Root(BaseResource):
    # Override to allow a POST to not be checked for authorization since
    # this is the only way to authorize.
    def __call__(self, request, *args, **kwargs):
        if request.method == 'POST':
            return super(BaseResource, self).__call__(request, *args, **kwargs)
        return super(Root, self).__call__(request, *args, **kwargs)

    def get(self, request):
        uri = request.build_absolute_uri

        return {
            'title': 'Serrano Hypermedia API',
            'version': API_VERSION,
            '_links': {
                'self': {
                    'href': uri(reverse('serrano:root')),
                },
                'fields': {
                    'href': uri(reverse('serrano:fields')),
                },
                'concepts': {
                    'href': uri(reverse('serrano:concepts')),
                },
                'contexts': {
                    'href': uri(reverse('serrano:contexts:active')),
                },
                'views': {
                    'href': uri(reverse('serrano:views:active')),
                },
                'queries': {
                    'href': uri(reverse('serrano:queries:active')),
                },
                'preview': {
                    'href': uri(reverse('serrano:data:preview')),
                },
                'exporter': {
                    'href': uri(reverse('serrano:data:exporter')),
                }
            }
        }

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                token = token_generator.make(user)
                data = self.get(request)
                data['token'] = token
                return data
        return HttpResponse('Invalid credentials', status=401)


root_resource = Root()

urlpatterns = patterns('', url(r'^$', root_resource, name='root'))
