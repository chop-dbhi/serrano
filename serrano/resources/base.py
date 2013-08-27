import functools
import re
from datetime import datetime
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from preserialize.serialize import serialize
from restlib2.params import Parametizer, param_cleaners
from restlib2.resources import Resource
from avocado.history.models import Revision
from avocado.models import DataContext, DataView, DataQuery
from . import templates
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

    # If attrs were supplied or derived from the request, validate them
    # and return as is. This provides support for one-off queries via POST
    # or GET.
    if isinstance(attrs, dict):
        klass.validate(attrs)
        return klass(json=attrs)

    # If an authenticated user made the request, filter by the user or
    # fallback to an active session key.
    if hasattr(request, 'user') and request.user.is_authenticated():
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

    # If an authenticated user made the request, filter by the user or
    # fallback to an active session key.
    if hasattr(request, 'user') and request.user.is_authenticated():
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

    def get_query(self, request, attrs=None):
        "Returns a DataQuery object based on `attrs` or the request."
        return get_request_query(request, attrs=attrs)

    @property
    def checks_for_orphans(self):
        return getattr(settings, 'SERRANO_CHECK_ORPHANED_FIELDS', True)


class DataResource(BaseResource):
    def __init__(self, **kwargs):
        self.rate_limit_count = getattr(settings, 'SERRANO_RATE_LIMIT_COUNT',
            self.rate_limit_count)
        self.rate_limit_seconds = getattr(settings,
            'SERRANO_RATE_LIMIT_SECONDS', self.rate_limit_seconds)

        self.auth_rate_limit_count = getattr(settings,
            'SERRANO_AUTH_RATE_LIMIT_COUNT', self.rate_limit_count)
        self.auth_rate_limit_seconds = getattr(settings,
            'SERRANO_AUTH_RATE_LIMIT_SECONDS', self.rate_limit_seconds)

        return super(DataResource, self).__init__(**kwargs)

    def is_too_many_requests(self, request, *arg, **kwargs):
        limit_count = self.rate_limit_count
        limit_seconds = self.rate_limit_seconds

        # Check for an identifier for this request. First, try to use the
        # user id and then try the session key as a fallback. If this is an
        # authenticated request then we prepend an indicator to the request
        # id and use the authenticated limiter settings.
        if hasattr(request, 'user') and request.user.is_authenticated():
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


class PaginatorParametizer(Parametizer):
    page = 1
    limit = 20

    def clean_page(self, value):
        return param_cleaners.clean_int(value)

    def clean_limit(self, value):
        return param_cleaners.clean_int(value)


class PaginatorResource(Resource):
    parametizer = PaginatorParametizer

    def get_paginator(self, queryset, limit):
        return Paginator(queryset, per_page=limit)

    def get_page_links(self, request, path, page, extra=None):
        "Returns the page links."
        uri = request.build_absolute_uri

        # format string will be expanded below
        params = {
            'page': '{0}',
            'limit': '{1}',
        }

        if extra:
            for key, value in extra.items():
                # Use the original GET parameter if supplied and if the
                # cleaned value is valid
                if key in request.GET and value is not None and value != '':
                    params.setdefault(key, request.GET.get(key))

        # Stringify parameters. Since these are the original GET params,
        # they do not need to be encoded
        pairs = sorted(['{0}={1}'.format(k, v) for k, v in params.items()])

        # Create path string
        path_format = '{0}?{1}'.format(path, '&'.join(pairs))

        limit = page.paginator.per_page

        links = {
            'self': {
                'href': uri(path_format.format(page.number, limit)),
            },
            'base': {
                'href': uri(path),
            }
        }

        if page.has_previous():
            links['prev'] = {
                'href': uri(path_format.format(page.previous_page_number(), limit)),
            }

        if page.has_next():
            links['next'] = {
                'href': uri(path_format.format(page.next_page_number(), limit)),
            }

        return links


def history_posthook(instance, data, request, object_uri, object_template,
        embed=False):
    uri = request.build_absolute_uri

    data['_links'] = {
        'self': {
            'href': uri(reverse("{0}:revision_for_object".format(object_uri),
                args=[instance.object_id, instance.pk])),
        },
        'object': {
            'href': uri(reverse("{0}:single".format(object_uri),
                args=[instance.object_id])),
        }
    }

    if embed:
        data['object'] = serialize(instance.content_object, **object_template)

    return data


class HistoryResource(DataResource):
    cache_max_age = 0
    private_cache = True

    object_model = None
    object_model_template = None
    object_model_base_uri = None

    model = Revision
    template = templates.Revision

    def prepare(self, request, instance, template=None):
        if template is None:
            template = self.template
        posthook = functools.partial(history_posthook, request=request,
                object_uri=self.object_model_base_uri,
                object_template=self.object_model_template)
        return serialize(instance, posthook=posthook, **template)

    def get_queryset(self, request, **kwargs):
        "Constructs a QuerySet for this user or session from past revisions."

        if not self.object_model:
            return self.model.objects.none()

        if hasattr(request, 'user') and request.user.is_authenticated():
            kwargs['user'] = request.user
        elif request.session.session_key:
            kwargs['session_key'] = request.session.session_key
        else:
            # The only case where kwargs is empty is for non-authenticated
            # cookieless agents.. e.g. bots, most non-browser clients since
            # no session exists yet for the agent.
            return self.model.objects.none()

        kwargs['content_type'] = ContentType.objects.get_for_model(
            self.object_model)

        return self.model.objects.filter(**kwargs)

    def get(self, request):
        queryset = self.get_queryset(request)
        return self.prepare(request, queryset)
