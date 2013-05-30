import re
import functools
from django.conf import settings
from restlib2.params import Parametizer
from restlib2.resources import Resource
from avocado.models import DataContext, DataView
from ..decorators import check_auth
from .. import cors

SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')

def _get_request_object(request, attrs=None, klass=None, key=None):
    """Resolves the appropriate object for use from the request.

    This applies only to DataView or DataContext objects.
    """
    # Attempt to derive the `attrs` from the request
    if attrs is None:
        if request.method == 'POST':
            attrs = request.data.get(key)
        elif request.method == 'GET':
            attrs = request.GET.get(key)

    # If attrs were supplied or derived from the request, validate them
    # and return as is. This provides support for one-off queries via POST
    # or GET.
    if isinstance(attrs, dict):
        klass.validate(attrs)
        return klass(json=attrs)

    # Ignore archived objects..
    kwargs = {
        'archived': False,
    }

    # If an authenticated user made the request, filter by the user or
    # fallback to an active session key.
    if hasattr(request, 'user') and request.user.is_authenticated():
        kwargs['user'] = request.user
    else:
        # If not session has been created, this is a cookie-less user agent
        # which is most likely a bot or a non-browser client (e.g. cURL).
        if request.session.session_key is None:
            return klass()
        kwargs['session_key'] = request.session.session_key

    # Assume it is a primary key and fallback to the sesssion
    try:
        kwargs['pk'] = int(attrs)
    except (ValueError, TypeError):
        kwargs['session'] = True

    try:
        return klass.objects.get(**kwargs)
    except klass.DoesNotExist:
        pass

    # Fallback to an instance based off the default template if one exists
    instance = klass()
    default = klass.objects.get_default_template()
    if default:
        instance.json = default.json
    return instance


# Partially applied functions for DataView and DataContext. These functions
# only require the request object and an optional `attrs` dict
get_request_view = functools.partial(_get_request_object,
    klass=DataView, key='view')
get_request_context = functools.partial(_get_request_object,
    klass=DataContext, key='context')


class BaseResource(Resource):
    param_defaults = None

    parametizer = Parametizer

    @check_auth
    def __call__(self, request, **kwargs):
        return super(BaseResource, self).__call__(request, **kwargs)

    def process_response(self, request, response):
        response = super(BaseResource, self).process_response(request, response)
        response = cors.patch_response(request, response, self.allowed_methods)
        return response

    def get_params(self, request):
        "Returns cleaned set of GET parameters."
        return self.parametizer().clean(request.GET, self.param_defaults)

    def get_context(self, request, attrs=None):
        "Returns a DataContext object based on `attrs` or the request."
        return get_request_context(request, attrs=attrs)

    def get_view(self, request, attrs=None):
        "Returns a DataView object based on `attrs` or the request."
        return get_request_view(request, attrs=attrs)
