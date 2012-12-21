from restlib2.resources import Resource
from avocado.models import DataContext, DataView


def _resolve_object(klass, key, request, attrs=None):
    """Resolves the appropriate object for use from the request. This is for
    DataView or DataContext objects only.
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

    return klass()


class BaseResource(Resource):
    param_defaults = {}

    def get_params(self, request):
        params = request.GET.copy()
        for param, default in self.param_defaults.items():
            params.setdefault(param, default)
        return params

    def get_context(self, request, attrs=None):
        "Returns a DataContext object based on `attrs` or the request."
        return _resolve_object(DataContext, 'context', request, attrs)

    def get_view(self, request, attrs=None):
        "Returns a DataView object based on `attrs` or the request."
        return _resolve_object(DataView, 'view', request, attrs)
