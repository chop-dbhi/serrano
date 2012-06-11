import json
from collections import defaultdict
from decimal import Decimal
from django.conf.urls import patterns, url
from django.db import router
from django.http import HttpResponse
from django.db.models import Q, Count
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_unicode
from restlib2 import utils
from modeltree.tree import trees
from avocado.conf import settings as _settings
from avocado.models import DataField
from avocado.stats import cluster as stats_cluster
from .base import BaseResource

DATA_CHOICES_MAP = _settings.DATA_CHOICES_MAP
SQLITE_AGG_EXT = getattr(settings, 'SQLITE_AGG_EXT', False)
AGG_FUNCTIONS = ['count', 'avg', 'min', 'max', 'stddev', 'variance']

# Apply the 'rule of thumb' for determining the appropriate number of
# clusters relative to the # of observations. Default to 50 to ensure
# a trend is somewhat visible
MINIMUM_OBSERVATIONS = 500
MAXIMUM_OBSERVATIONS = 20000

SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')

# Shortcuts defined ahead of time for transparency
can_change_datafield = lambda u: u.has_perm('avocado.change_datafield')


class DataFieldBase(BaseResource):
    param_defaults = {
        'query': '',
    }

    def get_queryset(self, request):
        queryset = DataField.objects.all()
        if not can_change_datafield(request.user):
            queryset = queryset.published()
        return queryset

    def get_object(self, request, **kwargs):
        queryset = self.get_queryset(request)
        try:
            return queryset.get(**kwargs)
        except DataField.DoesNotExist:
            pass

    def is_forbidden(self, request, response, *args, **kwargs):
        "Ensure non-privileged users cannot make any changes."
        if request.method not in SAFE_METHODS and not can_change_datafield(request.user):
            return True

    def is_not_found(self, request, response, pk=None, *args, **kwargs):
        if pk:
            instance = self.get_object(request, pk=pk)
            if instance is None:
                return True
            request.instance = instance
            return False


class DataFieldResource(DataFieldBase):
    "DataField Summary Resource"

    # Template for top-level attributes
    template = {
        'fields': [
            ':pk', 'name', 'plural_name', 'description', 'keywords',
            'category', 'app_name', 'model_name', 'field_name',
            'modified', 'published', 'archived', 'operators'
        ],
        'key_map': {
            'plural_name': 'get_plural_name',
            'operators': 'operator_choices',
        },
        'related': {
            'category': {
                'fields': [':pk', 'name', 'order', 'parent_id']
            },
        },
    }

    # Template for data-related attributes
    data_template = {
        'fields': [
            'type', 'modified', 'enumerable', 'searchable', 'unit',
            'plural_unit'
        ],
        'key_map': {
            'type': 'datatype',
            'modified': 'data_modified',
            'plural_unit': 'get_plural_unit',
        }
    }

    @classmethod
    def serialize(self, instance):
        obj = utils.serialize(instance, **self.template)
        obj['url'] = reverse('datafield', args=[instance.pk])
        obj['data'] = utils.serialize(instance, **self.data_template)

        obj['links'] = {
            'values': {
                'rel': 'data',
                'href': reverse('datafield-values', args=[instance.pk]),
            },
#            'stats': {
#                'rel': 'data',
#                'href': reverse('datafield-stats', args=[instance.pk]),
#            },
            'distribution': {
                'rel': 'data',
                'href': reverse('datafield-distribution', args=[instance.pk]),
            },
        }
        return obj

    def get(self, request, pk=None):
        params = self.get_params(request)

        # Process GET parameters
        sort = params.get('sort')        # default: model ordering
        direction = params.get('direction')  # default: desc
        published = params.get('published')
        archived = params.get('archived')
        query = params.get('query').strip()

        queryset = self.get_queryset(request)

        # For privileged users, check if any filters are applied
        if can_change_datafield(request.user):
            filters = {}

            if published == 'true':
                filters['published'] = True
            elif published == 'false':
                filters['published'] = False

            if archived == 'true':
                filters['archived'] = True
            elif archived == 'false':
                filters['archived'] = False

            if filters:
                queryset = queryset.filter(**filters)
        # For non-privileged users, filter out the non-published and archived
        else:
            queryset = queryset.published()

        # Early exit if dealing with a single object, no need to apply sorting
        if pk:
            return self.serialize(request.instance)

        # If there is a query parameter, perform the search
        if query:
            results = DataField.objects.search(query, queryset)
            return map(lambda x: self.serialize(x.object), results)

        # Apply sorting
        if sort == 'name':
            if direction == 'asc':
                queryset = queryset.order_by('name')
            else:
                queryset = queryset.order_by('-name')

        return map(self.serialize, queryset.iterator())


class DataFieldValues(DataFieldBase):
    "DataField Values Resource"

    def get(self, request, pk):
        instance = request.instance

        params = self.get_params(request)

        tree = trees[instance.model]
        context = self.get_context(request)
        queryset = context.apply(queryset=instance.query(), tree=tree)\
            .annotate(count=Count(instance.field_name))
        query = params.get('query').strip()

        if query:
            queryset = queryset.search_values(query)

        counts = {}
        for obj in queryset.iterator():
            counts[obj[instance.field_name]] = obj['count']

        results = []
        for value in instance.values:
            results.append({
                'name': smart_unicode(DATA_CHOICES_MAP.get(value, value)),
                'value': value,
                'count': counts.get(value, 0)
            })
        return results


class DataFieldStats(DataFieldBase):
    "DataField Stats Resource"

    def get(self, request, pk):
        instance = request.instance

        stats = instance.count()

        if instance.datatype == 'number':
            stats = stats.avg().max().min().sum()

            # SQLite does not support STDDEV and VARIANCE, so do not include
            # them unless the extension has been installed
            db = router.db_for_read(instance.model)
            if 'sqlite' not in settings.DATABASES[db]['ENGINE'] or SQLITE_AGG_EXT:
                stats = stats.stddev().variance()

        resp = iter(stats).next()
        resp['size'] = instance.size
        resp['mode'] = instance.count(instance.field_name).order_by('-count')[0]['value']
        resp['links'] = {
            'parent': {
                'rel': 'parent',
                'href': reverse('datafield', args=[instance.pk]),
            },
        }

        return resp


class DataFieldDistribution(DataFieldBase):
    "DataField Counts Resource"

    def get(self, request, pk):
        instance = request.instance

        params = self.get_params(request)

        # Only one grouping is currently supported
        dimensions = params.getlist('dimension')
        # aggregates = request.GET.getlist('aggregate')

        nulls = params.get('nulls')
        sort = params.get('sort')
        cluster = params.get('cluster')

        tree = trees[instance.model]

        # Get the appropriate data context
        context = self.get_context(request)
        queryset = context.apply(tree=tree)

        # Explicit fields to group by, ignore ones that dont exist or the
        # user does not have permission to view. Default is to group by the
        # reference field for distinct counts.
        if any(dimensions):
            fields = []
            groupby = []

            for pk in dimensions:
                f = self.get_object(request, pk=pk)
                if f:
                    fields.append(f)
                    groupby.append(tree.query_string_for_field(f.field))
        else:
            fields = [instance]
            groupby = [instance.field_name]

        # Always perform a count aggregation for the group since downstream
        # processing requires it to be present.
        stats = instance.groupby(*groupby).count()

        # Apply it relative to the queryset
        stats = stats.apply(queryset)

        # Exclude null values. Dependending on the downstream use of the data,
        # nulls may or may not be desirable.
        if nulls != 'true':
            q = Q()
            for field in groupby:
                q = q | Q(**{field: None})
            stats = stats.exclude(q)

        # Begin constructing the response
        resp = {
            'data': [],
            'outliers': [],
            'clustered': False,
            'size': 0,
        }

        # Evaluate list of points
        length = len(stats)

        # Nothing to do
        if not length:
            return resp

        if length > MAXIMUM_OBSERVATIONS:
            return HttpResponse(json.dumps({'error': 'Data too large'}), status=422)

        # Apply ordering. If any of the fields are enumerable, ordering should
        # be relative to those fields. For continuous data, the ordering is
        # relative to the count of each group
        if any([d.enumerable for d in fields]) and not sort == 'count':
            stats = stats.order_by(*groupby)
        else:
            stats = stats.order_by('-count')

        clustered = False
        points = list(stats)
        outliers = []

        # For N-dimensional continuous data, check if clustering should occur
        # to down-sample the data.
        if all([d.datatype == 'number' for d in fields]):
            # Extract observations for clustering
            obs = []
            for point in points:
                for i, dim in enumerate(point['values']):
                    if isinstance(dim, Decimal):
                        point['values'][i] = float(str(dim))
                obs.append(point['values'])

            # Perform k-means clustering. Determine centroids and calculate
            # the weighted count relatives to the centroid and observations
            # within the stats_cluster.
            if cluster != 'false' and length >= MINIMUM_OBSERVATIONS:
                clustered = True

                result = stats_cluster.kmeans_optm(obs)
                outliers = [points[i] for i in result['outliers']]

                dist_weights = defaultdict(lambda: {'dist': [], 'count': []})
                for i, idx in enumerate(result['indexes']):
                    dist_weights[idx]['dist'].append(result['distances'][i])
                    dist_weights[idx]['count'].append(points[i]['count'])

                points = []

                # Determine best count relative to each piont in the cluster
                # TODO improve this step, use numpy arrays
                for i, centroid in enumerate(result['centroids']):
                    dist_sum = sum(dist_weights[i]['dist'])
                    weighted_counts = []
                    for j, dist in enumerate(dist_weights[i]['dist']):
                        if dist_sum:
                            wc = (1 - dist / dist_sum) * dist_weights[i]['count'][j]
                        else:
                            wc = dist_weights[i]['count'][j]
                        weighted_counts.append(wc)

                    values = list(centroid)
                    points.append({
                        'values': values,
                        'count': int(sum(weighted_counts)),
                    })
            else:
                indexes = stats_cluster.find_outliers(obs, whitened=False)

                outliers = []
                for idx in indexes:
                    outliers.append(points[idx])
                    points[idx] = None
                points = [p for p in points if p is not None]

        return {
            'data': points,
            'clustered': clustered,
            'outliers': outliers,
            'size': length,
        }


# Resource endpoints
urlpatterns = patterns('',
    url(r'^$', DataFieldResource(), name='datafield'),
    url(r'^(?P<pk>\d+)/$', DataFieldResource(), name='datafield'),
    url(r'^(?P<pk>\d+)/values/$', DataFieldValues(), name='datafield-values'),
    url(r'^(?P<pk>\d+)/stats/$', DataFieldStats(), name='datafield-stats'),
    url(r'^(?P<pk>\d+)/dist/$', DataFieldDistribution(), name='datafield-distribution'),
)
