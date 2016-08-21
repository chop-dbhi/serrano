import functools

from datetime import datetime
from django.core.cache import cache
from restlib2.params import Parametizer
from restlib2.resources import Resource
from avocado.models import DataContext, DataView, DataQuery
from serrano.conf import settings
from django.contrib.auth import authenticate, login
from ..tokens import get_request_token
from .. import cors
from .. import links

__all__ = ('BaseResource', 'ThrottledResource')

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

    # If the `attrs` still could not be resolved, try to get the view or
    # context from the query data if it exists within the request.
    if attrs is None:
        request_data = None

        # Try to read the query data from the request
        if request.method == 'POST':
            request_data = request.data.get('query')
        elif request.method == 'GET':
            request_data = request.GET.get('query')

        # If query data was found in the request, then attempt to create a
        # DataQuery object from it.
        if request_data:
            query = get_request_query(request, attrs=request_data.get('query'))

            # Now that the DataQuery object is built, read the appropriate
            # attribute from it, returning None if the attribute wasn't found.
            # Since `context` and `view` are the keys used in get_request_view
            # and get_request_context respectively, we can use the key directly
            # to access the context and view properties of the DataQuery model.
            key_object = getattr(query, key, None)

            # If the property exists and is not None, then read the json from
            # the object as both DataContext and DataView objects will have a
            # json property. This json will be used as the attributes to
            # construct or lookup the klass object going forward. Otherwise,
            # `attrs` will still be None and we are no worse off than we were
            # before attempting to create and read the query.
            if key_object:
                attrs = key_object.json

    # Use attrs that were supplied or derived from the request.
    # This provides support for one-off queries via POST or GET.
    if isinstance(attrs, (list, dict)):
        return klass(json=attrs)

    kwargs = {}

    # If an authenticated user made the request, filter by the user or
    # fallback to an active session key.
    if getattr(request, 'user', None) and request.user.is_authenticated():
        kwargs['user'] = request.user
    else:
        # If no session has been created, this is a cookie-less user agent
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
        # Check that multiple DataViews or DataContexts are not returned
        # If there are more than one, return the most recent
        return klass.objects.filter(**kwargs).latest('modified')
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
get_request_view = functools.partial(
    _get_request_object, klass=DataView, key='view')
get_request_context = functools.partial(
    _get_request_object, klass=DataContext, key='context')


def get_request_query(request, attrs=None):
    """
    Resolves the appropriate DataQuery object for use from the request.
    """
    # Attempt to derive the `attrs` from the request
    if attrs is None:
        if request.method == 'POST':
            attrs = request.data.get('query')
        elif request.method == 'GET':
            attrs = request.GET.get('query')

    # If the `attrs` could not be derived from the request(meaning no query
    # was explicity defined), try to construct the query by deriving a context
    # and view from the request.
    if attrs is None:
        json = {}

        context = get_request_context(request)
        if context:
            json['context'] = context.json

        view = get_request_view(request)
        if view:
            json['view'] = view.json

        return DataQuery(json)

    # If `attrs` were derived or supplied then validate them and return a
    # DataQuery based off the `attrs`.
    if isinstance(attrs, dict):
        # We cannot simply validate and create a DataQuery based off the
        # `attrs` as they are now because the context and or view might not
        # contain json but might instead be a pk or some other value. Use the
        # internal helper methods to construct the context and view objects
        # and build the query from the json of those objects' json.
        json = {}

        context = get_request_context(request, attrs=attrs)
        if context:
            json['context'] = context.json
        view = get_request_view(request, attrs=attrs)
        if view:
            json['view'] = view.json

        DataQuery.validate(json)
        return DataQuery(json)

    kwargs = {}

    # If an authenticated user made the request, filter by the user or
    # fallback to an active session key.
    if getattr(request, 'user', None) and request.user.is_authenticated():
        kwargs['user'] = request.user
    else:
        # If not session has been created, this is a cookie-less user agent
        # which is most likely a bot or a non-browser client (e.g. cURL).
        if request.session.session_key is None:
            return DataQuery()
        kwargs['session_key'] = request.session.session_key

    # Assume it is a primary key and fallback to the sesssion
    try:
        kwargs['pk'] = int(attrs)
    except (ValueError, TypeError):
        kwargs['session'] = True

    try:
        return DataQuery.objects.get(**kwargs)
    except DataQuery.DoesNotExist:
        pass

    # Fallback to an instance based off the default template if one exists
    instance = DataQuery()
    default = DataQuery.objects.get_default_template()
    if default:
        instance.json = default.json
    return instance


class BaseResource(Resource):
    param_defaults = None

    parametizer = Parametizer

    def is_unauthorized(self, request, *args, **kwargs):
        if cors.is_preflight(request):
            return

        user = getattr(request, 'user', None)

        # Attempt to authenticate if a token is present
        if not user or not user.is_authenticated():
            token = get_request_token(request)
            user = authenticate(token=token)

            if user:
                login(request, user)
            elif settings.AUTH_REQUIRED:
                return True

    def process_response(self, request, response):
        response = super(BaseResource, self).process_response(
            request, response)

        response = cors.patch_response(request, response, self.allowed_methods)

        response = links.patch_response(
            request, response, self.get_links(request),
            self.get_link_templates(request))

        return response

    def get_links(self, request):
        "Returns the links to include in the headers of responses"
        return {}

    def get_link_templates(self, request):
        "Returns the link templates to include in the headers of responses"
        return {}

    def get_params(self, request):
        "Returns cleaned set of GET parameters."
        return self.parametizer().clean(request.GET, self.param_defaults)

    def get_context(self, request, attrs=None):
        "Returns a DataContext object based on `attrs` or the request."
        return get_request_context(request, attrs=attrs)

    def get_view(self, request, attrs=None):
        "Returns a DataView object based on `attrs` or the request."
        return get_request_view(request, attrs=attrs)

    def get_query(self, request, attrs=None):
        "Returns a DataQuery object based on `attrs` or the request."
        return get_request_query(request, attrs=attrs)

    @property
    def checks_for_orphans(self):
        return settings.CHECK_ORPHANED_FIELDS


class ThrottledResource(BaseResource):
    def __init__(self, **kwargs):
        if settings.RATE_LIMIT_COUNT:
            self.rate_limit_count = settings.RATE_LIMIT_COUNT

        if settings.RATE_LIMIT_SECONDS:
            self.rate_limit_seconds = settings.RATE_LIMIT_SECONDS

        self.auth_rate_limit_count = settings.AUTH_RATE_LIMIT_COUNT \
            or self.rate_limit_count

        self.auth_rate_limit_seconds = settings.AUTH_RATE_LIMIT_SECONDS \
            or self.rate_limit_seconds

        return super(ThrottledResource, self).__init__(**kwargs)

    def is_too_many_requests(self, request, *arg, **kwargs):
        limit_count = self.rate_limit_count
        limit_seconds = self.rate_limit_seconds

        # Check for an identifier for this request. First, try to use the
        # user id and then try the session key as a fallback. If this is an
        # authenticated request then we prepend an indicator to the request
        # id and use the authenticated limiter settings.
        if getattr(request, 'user', None) and request.user.is_authenticated():
            request_id = "auth:{0}".format(request.user.id)
            limit_count = self.auth_rate_limit_count
            limit_seconds = self.auth_rate_limit_seconds
        elif request.session.session_key:
            request_id = request.session.session_key
        else:
            # The only time we should reach this point is for
            # non-authenitcated, cookieless agents(bots). Simply return False
            # here and let other methods decide how to deal with the bot.
            return False

        # Construct the cache key from the request identifier and lookup
        # the current cached value for the key. The counts that are stored in
        # the cache are tuples where the 1st value is the request count for
        # the given time interval and the 2nd value is the start of the
        # time interval.
        cache_key = 'serrano:data_request:{0}'.format(request_id)
        current_count = cache.get(cache_key)

        # If there is nothing cached for this key then add a new cache value
        # with a count of 1 and interval starting at the current date and time.
        # Obviously, if nothing is cached then we can't have had too many
        # requests as this is the first one so we return False here.
        if current_count is None:
            cache.set(cache_key, (1, datetime.now()))
            return False
        else:
            # Calculate the time in seconds between the current date and time
            # and the interval start from the cached value.
            interval = (datetime.now() - current_count[1]).seconds

            # If we have exceeded the interval size then reset the interval
            # start time and reset the request count to 1 since we are on a
            # new interval now.
            if interval > limit_seconds:
                cache.set(cache_key, (1, datetime.now()))
                return False

            # Update the request count to account for this request
            new_count = current_count[0] + 1
            cache.set(cache_key, (new_count, current_count[1]))

            # Since we are still within the interval, just check if we have
            # exceeded the request limit or not and return the result of the
            # comparison.
            return new_count > limit_count
