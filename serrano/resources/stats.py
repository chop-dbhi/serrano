from django.core.urlresolvers import reverse
from django.conf.urls import patterns, url
from django.views.decorators.cache import never_cache
from restlib2.params import Parametizer, BoolParam, StrParam
from avocado.models import DataContext, DataField
from avocado.query import pipeline
from .base import BaseResource, ThrottledResource


class StatsResource(BaseResource):
    def get(self, request):
        uri = request.build_absolute_uri

        return {
            'title': 'Serrano Stats Endpoint',
            '_links': {
                'self': {
                    'href': uri(reverse('serrano:stats:root')),
                },
                'counts': {
                    'href': uri(reverse('serrano:stats:counts')),
                },
            }
        }


class CountStatsParametizer(Parametizer):
    aware = BoolParam(False)
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

        data = []
        models = set()
        QueryProcessor = pipeline.query_processors[params['processor']]

        for app_name, model_name in model_names:
            # DataField used here to resolve foreign key-based fields.
            model = DataField(app_name=app_name, model_name=model_name).model

            # Foreign-key based fields may resolve to models that are already
            # accounted for.
            if model in models:
                continue

            models.add(model)

            # Build a queryset through the context which is toggled by
            # the parameter.
            processor = QueryProcessor(context=context, tree=model)
            queryset = processor.get_queryset(request=request)
            count = queryset.values('pk').distinct().count()

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

            data.append({
                'count': count,
                'app_name': app_name,
                'model_name': model_name,
                'verbose_name': verbose_name,
                'verbose_name_plural': verbose_name_plural,
            })

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
