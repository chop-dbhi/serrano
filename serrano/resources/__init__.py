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
from ..links import reverse_tmpl

API_VERSION = '{major}.{minor}.{micro}'.format(**serrano.__version_info__)


class Root(BaseResource):
    # Override to allow a POST to not be checked for authorization since
    # this is the only way to authorize.
    def is_unauthorized(self, request, *args, **kwargs):
        if request.method != 'POST':
            return super(Root, self).is_unauthorized(request, *args, **kwargs)

    def get_link_templates(self, request):
        uri = request.build_absolute_uri

        return {
            'category': reverse_tmpl(uri, 'serrano:category', {
                'pk': (int, 'id')
            }),
            'field': reverse_tmpl(uri, 'serrano:field', {
                'pk': (int, 'id')
            }),
            'concept': reverse_tmpl(uri, 'serrano:concept', {
                'pk': (int, 'id')
            }),
            'context': reverse_tmpl(uri, 'serrano:contexts:single', {
                'pk': (int, 'id')
            }),
            'view': reverse_tmpl(uri, 'serrano:views:single', {
                'pk': (int, 'id')
            }),
            'query': reverse_tmpl(uri, 'serrano:queries:single', {
                'pk': (int, 'id')
            }),
            'query_results': reverse_tmpl(uri, 'serrano:queries:results', {
                'pk': (int, 'id')
            }),
            'export': reverse_tmpl(uri, 'serrano:data:exporter', {
                'export_type': (str, 'type')
            }),
        }

    def get_links(self, request):
        uri = request.build_absolute_uri

        links = {
            'self': uri(reverse('serrano:root')),
            'categories': uri(reverse('serrano:categories')),
            'fields': uri(reverse('serrano:fields')),
            'concepts': uri(reverse('serrano:concepts')),
            'contexts': uri(reverse('serrano:contexts:active')),
            'views': uri(reverse('serrano:views:active')),
            'queries': uri(reverse('serrano:queries:active')),
            'public_queries': uri(reverse('serrano:queries:public')),
            'async_preview': uri(reverse('serrano:async:preview')),
            'preview': uri(reverse('serrano:data:preview')),
            'async_exporter': uri(reverse('serrano:async:exporter')),
            'exporter': uri(reverse('serrano:data:exporter')),
            'ping': uri(reverse('serrano:ping')),
            'stats': uri(reverse('serrano:stats:root')),
        }

        if dep_supported('objectset'):
            links['sets'] = uri(reverse('serrano:sets:root'))

        return links

    def get(self, request):
        return {
            'title': 'Serrano Hypermedia API',
            'version': API_VERSION,
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
