import json
from collections import defaultdict
from decimal import Decimal
from django.conf.urls import patterns, url
from django.http import HttpResponse
from django.db.models import Q
from django.conf import settings
from django.core.urlresolvers import reverse
from restlib2.http import codes
from preserialize.serialize import serialize
from modeltree.tree import trees
from avocado.models import DataField
from avocado.conf import OPTIONAL_DEPS
from .base import BaseResource
from . import templates

SQLITE_AGG_EXT = getattr(settings, 'SQLITE_AGG_EXT', False)
AGGREGATION_FUNCTIONS = ['count', 'avg', 'min', 'max', 'stddev', 'variance']

MINIMUM_OBSERVATIONS = 500
MAXIMUM_OBSERVATIONS = 50000

MAXIMUM_RANDOM = 100

SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')

# Shortcuts defined ahead of time for transparency
can_change_datafield = lambda u: u.has_perm('avocado.change_datafield')


stats_capable = lambda x: not x.searchable and not x.internal_type == 'auto'


class DataFieldBase(BaseResource):
    template = templates.DataField

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

    # Augment the pre-serialized object
    @classmethod
    def prepare(self, instance):
        obj = serialize(instance, **self.template)

        # Augment the links
        obj['_links'] = {
            'self': {
                'rel': 'self',
                'href': reverse('serrano:datafield', args=[instance.pk]),
            },
            'values': {
                'rel': 'data',
                'href': reverse('serrano:datafield-values', args=[instance.pk]),
            },
        }

        if stats_capable(instance):
            obj['_links']['stats'] = {
                'rel': 'data',
                'href': reverse('serrano:datafield-stats', args=[instance.pk]),
            }
            # Add distribution link only if the relevent dependencies are
            # installed.
            if OPTIONAL_DEPS['scipy']:
                obj['_links']['distribution'] = {
                    'rel': 'data',
                    'href': reverse('serrano:datafield-distribution', args=[instance.pk]),
                }

        return obj

    def is_forbidden(self, request, response, *args, **kwargs):
        "Ensure non-privileged users cannot make any changes."
        if request.method not in SAFE_METHODS and not can_change_datafield(request.user):
            return True

    def is_not_found(self, request, response, pk, *args, **kwargs):
        instance = self.get_object(request, pk=pk)
        if instance is None:
            return True
        request.instance = instance
        return False


class DataFieldResource(DataFieldBase):
    "DataField Resource"
    def get(self, request, pk):
        return self.prepare(request.instance)


class DataFieldsResource(DataFieldResource):
    "DataField Collection Resource"

    def is_not_found(self, request, response, *args, **kwargs):
        return False

    def get(self, request):
        params = self.get_params(request)

        # Process GET parameters
        sort = params.get('sort')               # default: model ordering
        direction = params.get('direction')     # default: desc
        published = params.get('published')
        archived = params.get('archived')

        # This is only application if Haystack is setup
        if OPTIONAL_DEPS['haystack']:
            query = params.get('query').strip()
        else:
            query = ''

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

        # If there is a query parameter, perform the search
        if query:
            results = DataField.objects.search(query, queryset)
            objects = map(lambda x: x.object, results)
        else:
            # Apply sorting
            if sort == 'name':
                if direction == 'asc':
                    queryset = queryset.order_by('name')
                else:
                    queryset = queryset.order_by('-name')
            objects = queryset.iterator()

        return map(self.prepare, objects)


class DataFieldValues(DataFieldBase):
    """DataField Values Resource

    This resource can be overriden for any datafield to use a more
    performant search implementation.
    """

    def get(self, request, pk):
        instance = request.instance

        params = self.get_params(request)

        if OPTIONAL_DEPS['haystack']:
            query = params.get('query').strip()
        else:
            query = ''

        try:
            random = min(int(params.get('random')), MAXIMUM_RANDOM)
        except (ValueError, TypeError):
            random = False

        results = []

        # If a query term is supplied, perform the icontains search
        if query:
            for value in instance.search(query):
                results.append({
                    'label': instance.get_label(value),
                    'value': value,
                })
        # get a random set of values
        elif random:
            queryset = instance.model.objects\
                .only(instance.field_name).order_by('?')[:random]
            for obj in queryset:
                value = getattr(obj, instance.field_name)
                results.append({
                    'label': instance.get_label(value),
                    'value': value,
                })
        # ..otherwise use the cached choices
        else:
            for value, name in instance.choices:
                results.append({
                    'label': name,
                    'value': value,
                })
        return results


class DataFieldStats(DataFieldBase):
    "DataField Stats Resource"

    def get(self, request, pk):
        instance = request.instance

        stats = None

        if instance.simple_type == 'number':
            stats = instance.max().min().avg()
        elif instance.simple_type == 'string' and instance.enumerable:
            stats = instance.count(distinct=True)

        if stats is None:
            resp = {}
        else:
            resp = next(iter(stats))

        resp['_links'] = {
            'parent': {
                'rel': 'parent',
                'href': reverse('serrano:datafield', args=[instance.pk]),
            },
        }

        return resp


datafield_resource = DataFieldResource()
datafields_resource = DataFieldsResource()
datafield_values = DataFieldValues()
datafield_stats = DataFieldStats()

# Resource endpoints
urlpatterns = patterns('',
    url(r'^$', datafields_resource, name='datafields'),
    url(r'^(?P<pk>\d+)/$', datafield_resource, name='datafield'),
    url(r'^(?P<pk>\d+)/values/$', datafield_values, name='datafield-values'),
    url(r'^(?P<pk>\d+)/stats/$', datafield_stats, name='datafield-stats'),
)


# If the Avocado extensions are installed, add the distribution resource
if OPTIONAL_DEPS['scipy']:
    from avocado.stats import cluster as stats_cluster

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
            # Perform clustering
            cluster = params.get('cluster')
            relative = params.get('relative')
            k = params.get('n')

            tree = trees[instance.model]

            # Get the appropriate data context
            context = self.get_context(request)
            queryset = context.apply(tree=tree).distinct()

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
                groupby = [tree.query_string_for_field(instance.field)]

            # Always perform a count aggregation for the group since downstream
            # processing requires it to be present.
            stats = instance.groupby(*groupby).count()#\
#                .filter(**{'{}__{}__isnull'\
#                    .format(root_opts.module_name, root_opts.pk.name): False})

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
                return HttpResponse(json.dumps({'error': 'Data too large'}),
                    status=codes.unprocessable_entity)

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
            if all([d.simple_type == 'number' for d in fields]):
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

                    result = stats_cluster.kmeans_optm(obs, k=k)
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

    datafield_dist_resource = DataFieldDistribution()

    urlpatterns += patterns('',
        url(r'^(?P<pk>\d+)/dist/$', datafield_dist_resource,
            name='datafield-distribution'),
    )
