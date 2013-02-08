from django.http import HttpResponse
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from django.contrib.auth import authenticate, login
from serrano.tokens import token_generator
from .base import BaseResource


class Root(BaseResource):
    # Override to allow a POST to not be checked for authorization since
    # this is the only way to authorize.
    def __call__(self, request, *args, **kwargs):
        if request.method == 'POST':
            return super(BaseResource, self).__call__(request, *args, **kwargs)
        return super(Root, self).__call__(request, *args, **kwargs)

    def get(self, request):
        return {
            'title': 'Serrano Hypermedia API',
            '_links': {
                'self': {
                    'rel': 'self',
                    'href': reverse('serrano:root'),
                },
                'fields': {
                    'rel': 'datafields',
                    'href': reverse('serrano:datafields'),
                },
                'concepts': {
                    'rel': 'dataconcepts',
                    'href': reverse('serrano:dataconcepts'),
                },
                'contexts': {
                    'rel': 'datacontexts',
                    'href': reverse('serrano:contexts:active'),
                },
                'views': {
                    'rel': 'dataviews',
                    'href': reverse('serrano:views:active'),
                },
                'preview': {
                    'rel': 'data',
                    'href': reverse('serrano:data:preview'),
                },
                'exporter': {
                    'rel': 'data',
                    'href': reverse('serrano:data:exporter'),
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
                return {'token': token}
        return HttpResponse('Invalid credentials', status=401)



root_resource = Root()

urlpatterns = patterns('',
    url(r'^$', root_resource, name='root')
)
