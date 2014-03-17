from urlparse import urlparse
from django.utils.http import is_safe_url
from django.conf import settings as django_settings
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from django.contrib.auth import authenticate, login
from restlib2.resources import Resource
from restlib2.http import codes
import serrano
from serrano.conf import dep_supported, settings
from serrano.tokens import token_generator
from serrano import cors
from .base import BaseResource

API_VERSION = '{major}.{minor}.{micro}'.format(**serrano.__version_info__)


class Root(BaseResource):
    # Override to allow a POST to not be checked for authorization since
    # this is the only way to authorize.
    def is_unauthorized(self, request, *args, **kwargs):
        if request.method != 'POST':
            return super(Root, self).is_unauthorized(request, *args, **kwargs)

    def get(self, request):
        uri = request.build_absolute_uri

        data = {
            'title': 'Serrano Hypermedia API',
            'version': API_VERSION,
            '_links': {
                'self': {
                    'href': uri(reverse('serrano:root')),
                },
                'categories': {
                    'href': uri(reverse('serrano:categories')),
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
                'public_queries': {
                    'href': uri(reverse('serrano:queries:public')),
                },
                'preview': {
                    'href': uri(reverse('serrano:data:preview')),
                },
                'exporter': {
                    'href': uri(reverse('serrano:data:exporter')),
                },
                'ping': {
                    'href': uri(reverse('serrano:ping')),
                },
            }
        }

        if dep_supported('objectset'):
            data['_links']['sets'] = {
                'href': uri(reverse('serrano:sets:root')),
            }

        return data

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

        return self.render(request, {'message': 'Invalid credentials'},
                           status=codes.unauthorized)


class Ping(Resource):
    """Dedicated resource for pinging the service. This is used for detecting
    session timeouts. This resource does not impact the session on a request
    and thus allows for the session to naturally timeout.

    The response code will always be 200, however the payload will contain the
    real code and status, such as 'timeout', with any other relevant
    information. This decision was facilitate browser clients whose behavior
    will vary when using real response codes.
    """
    def process_response(self, request, response):
        response = super(Ping, self).process_response(request, response)
        return cors.patch_response(request, response, self.allowed_methods)

    def get(self, request):
        resp = {
            'code': codes.ok,
            'status': 'ok',
        }

        if settings.AUTH_REQUIRED:
            user = getattr(request, 'user')

            if not user or not user.is_authenticated():
                ref = request.META.get('HTTP_REFERER', '')

                if ref and is_safe_url(url=ref, host=request.get_host()):
                    # Construct redirect to referring page since redirecting
                    # back to an API endpoint does not useful
                    path = urlparse(ref).path
                else:
                    path = django_settings.LOGIN_REDIRECT_URL

                location = '{0}?next={1}'.format(django_settings.LOGIN_URL,
                                                 path)
                url = request.build_absolute_uri(location)

                resp = {
                    'code': codes.found,
                    'status': 'timeout',
                    'location': url,
                }

        return self.render(request, resp)


root_resource = Root()
ping_resource = Ping()

urlpatterns = patterns(
    '',
    url(r'^$', root_resource, name='root'),
    url(r'^ping/$', ping_resource, name='ping'),
)
