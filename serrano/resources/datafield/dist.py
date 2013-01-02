import json
from decimal import Decimal
from collections import defaultdict
from django.db.models import Q
from django.http import HttpResponse
from restlib2.http import codes
from modeltree.tree import trees
from avocado.stats import cluster as stats_cluster
from .base import DataFieldBase


MINIMUM_OBSERVATIONS = 500
MAXIMUM_OBSERVATIONS = 50000


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
#                .filter(**{'{0}__{1}__isnull'\
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
