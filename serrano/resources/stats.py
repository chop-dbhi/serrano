import weakref
import threading
from multiprocessing.pool import ThreadPool
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.conf.urls import patterns, url
from django.views.decorators.cache import never_cache
from restlib2.params import Parametizer, BoolParam, StrParam
from avocado.models import DataContext, DataField
from avocado.query import pipeline
from avocado.core.cache import cache_key
from avocado.core.cache.model import NEVER_EXPIRE
from ..conf import settings
from .base import BaseResource, ThrottledResource


def get_count(request, model, refresh, processor, context):
    opts = model._meta

    # Build a queryset through the context which is toggled by
    # the parameter.
    processor = processor(context=context, tree=model)
    queryset = processor.get_queryset(request=request)

    # Get count from cache or database
    label = ':'.join([opts.app_label, opts.module_name, 'count'])
    key = cache_key(label, kwargs={'queryset': queryset})

    if refresh:
        count = None
    else:
        count = cache.get(key)

    if count is None:
        count = queryset.values('pk').distinct().count()
        cache.set(key, count, timeout=NEVER_EXPIRE)

    # Close the connection in the thread to prevent 'idle in transaction'
    # situtations.
    from django.db import connection
    connection.close()

    return count


class StatsResource(BaseResource):
    def get_links(self, request):
        uri = request.build_absolute_uri

        return {
            'self': uri(reverse('serrano:stats:root')),
            'counts': uri(reverse('serrano:stats:counts'))
        }

    def get(self, request):
        return {
            'title': 'Serrano Stats Endpoint',
        }


class CountStatsParametizer(Parametizer):
    aware = BoolParam(False)
    refresh = BoolParam(False)
    processor = StrParam('default', choices=pipeline.query_processors)


class CountStatsResource(ThrottledResource):
    parametizer = CountStatsParametizer

    def get(self, request):
        params = self.get_params(request)

        if params['aware']:
            context = self.get_context(request)
        else:
            context = DataContext()

        # Get all published app/model pairs to produce counts for.
        model_names = DataField.objects.published()\
            .values_list('app_name', 'model_name')\
            .order_by('model_name').distinct()

        results = []
        data = []
        models = set()

        QueryProcessor = pipeline.query_processors[params['processor']]

        # Workaround for a Python bug for versions 2.7.5 and below
        # http://bugs.python.org/issue10015
        if not hasattr(threading.current_thread(), '_children'):
            threading.current_thread()._children = weakref.WeakKeyDictionary()

        # Pool of threads to execute the counts in parallel
        pool = ThreadPool()

        for app_name, model_name in model_names:
            # DataField used here to resolve foreign key-based fields.
            model = DataField(app_name=app_name, model_name=model_name).model

            # No redundant counts
            if model in models:
                continue

            models.add(model)

            opts = model._meta

            # Format is called to resolve Django's internal proxy wrapper.
            verbose_name = opts.verbose_name.format()
            verbose_name_plural = opts.verbose_name_plural.format()

            # Assume no custom verbose_name as been set in Meta class, so
            # apply a minimal title-case.
            if verbose_name.islower():
                verbose_name = verbose_name.title()

            if verbose_name_plural.islower():
                verbose_name_plural = verbose_name_plural.title()

            # Placeholder with the model name. The count will be replaced if
            # successful.
            data.append({
                'count': None,
                'app_name': app_name,
                'model_name': model_name,
                'verbose_name': verbose_name,
                'verbose_name_plural': verbose_name_plural,
            })

            # Asynchronously execute the count
            result = pool.apply_async(get_count, args=(
                request,
                model,
                params['refresh'],
                QueryProcessor,
                context
            ))

            results.append(result)

        pool.close()

        for i, r in enumerate(results):
            try:
                count = r.get(timeout=settings.STATS_COUNT_TIMEOUT)
                data[i]['count'] = count
            except Exception:
                pass

        return data

    # Same logic, but supports submitting context via a POST.
    post = get


stats_resource = never_cache(StatsResource())
counts_resource = never_cache(CountStatsResource())


# Resource endpoints
urlpatterns = patterns(
    '',

    url(r'^$', stats_resource, name='root'),

    url(r'^counts/$', counts_resource, name='counts'),
)
