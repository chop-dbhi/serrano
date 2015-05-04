try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from django.http import Http404
from modeltree.tree import MODELTREE_DEFAULT_ALIAS, trees
from restlib2.params import Parametizer, IntParam, StrParam
from avocado.query import pipeline, utils
from avocado.export import HTMLExporter
from .base import BaseResource
from ..links import patch_response


def get_page_links(request, path, page, limit, extra=None):
    "Returns the page links."
    uri = request.build_absolute_uri

    if not page:
        return {
            'self': uri(path),
        }

    # Format string will be expanded below.
    if limit:
        params = {
            'limit': '{limit}',
            'page': '{page}',
        }
    else:
        limit = None
        params = {
            'limit': '0',
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

    links = {
        'self': uri(path_format.format(page=page, limit=limit)),
        'base': uri(path),
        'first': uri(path_format.format(page=1, limit=limit)),
    }

    if page > 1:
        prev_page = page - 1
        links['prev'] = uri(path_format.format(
            page=prev_page, limit=limit))

    next_page = page + 1
    links['next'] = uri(path_format.format(
        page=next_page, limit=limit))

    return links


class PreviewParametizer(Parametizer):
    limit = IntParam(20)
    processor = StrParam('default', choices=pipeline.query_processors)
    reader = StrParam('cached', choices=HTMLExporter.readers)
    tree = StrParam(MODELTREE_DEFAULT_ALIAS, choices=trees)


class PreviewResource(BaseResource):
    """Resource for *previewing* data prior to exporting.

    Data is formatted using a JSON+HTML exporter which prefers HTML formatted
    or plain strings. Browser-based clients can consume the JSON and render
    the HTML for previewing.
    """

    parametizer = PreviewParametizer

    def get(self, request, **kwargs):
        params = self.get_params(request)

        limit = params.get('limit')
        tree = params.get('tree')

        page = kwargs.get('page')
        stop_page = kwargs.get('stop_page')

        offset = None

        # Restrict the preview results to a particular page or page range.
        if page:
            page = int(page)

            # Pages are 1-based
            if page < 1:
                raise Http404

            # Change to 0-base for calculating offset
            offset = limit * (page - 1)

            if stop_page:
                stop_page = int(stop_page)

                # Cannot have a lower index than page
                if stop_page < page:
                    raise Http404

                # 4...5 means 4 and 5, not everything up to 5 like with
                # list slices, so 4...4 is equivalent to just 4
                if stop_page > page:
                    limit = limit * stop_page
        else:
            limit = None

        # Get the request's view and context
        view = self.get_view(request)
        context = self.get_context(request)

        # Initialize a query processor
        QueryProcessor = pipeline.query_processors[params['processor']]
        processor = QueryProcessor(context=context, view=view, tree=tree)

        # Build a queryset for pagination and other downstream use
        queryset = processor.get_queryset(request=request)

        # Isolate this query and subsequent queries to a named connection.
        # Cancel the outstanding query if one is present.
        query_name = request.session.session_key
        utils.cancel_query(query_name)

        queryset = utils.isolate_queryset(query_name, queryset)

        # 0 limit means all for pagination, however the read method requires
        # an explicit limit of None
        limit = limit or None

        # Prepare an HTMLExporter
        exporter = processor.get_exporter(HTMLExporter)

        objects = []

        # This is an optimization when concepts are selected for ordering
        # only. There is not guarantee to how many rows are required to get
        # the desired `limit` of rows, so the query is unbounded. If all
        # ordering facets are visible, the limit and offset can be pushed
        # down to the query.
        view_node = view.parse()
        order_only = lambda f: not f.get('visible', True)

        if filter(order_only, view_node.facets):
            iterable = processor.get_iterable(queryset=queryset,
                                              request=request)

            rows = exporter.manual_read(iterable,
                                        request=request,
                                        offset=offset,
                                        limit=limit)
        else:
            iterable = processor.get_iterable(queryset=queryset,
                                              request=request,
                                              limit=limit,
                                              offset=offset)

            # Get the requested reader
            reader = params['reader']
            method = exporter.reader(reader)

            rows = method(iterable, request=request)

        objects = []

        # Split the primary key from the requested values in the row.
        for row in rows:
            objects.append({
                'pk': row[0],
                'values': row[1:],
            })

        header = []
        concepts = view_node.get_concepts_for_select()
        ordering = OrderedDict(view_node.ordering)

        # Skip the primary key field in the header since it is not exposed
        # in the row output below.
        for i, f in enumerate(exporter.header[1:]):
            concept = concepts[i]

            obj = {
                'id': concept.id,
                'name': f['label'],
            }

            if concept.id in ordering:
                obj['direction'] = ordering[concept.id]

            header.append(obj)

        # Various model options
        opts = queryset.model._meta

        model_name = opts.verbose_name.format()
        model_name_plural = opts.verbose_name_plural.format()

        data = {
            'keys': header,
            'items': objects,
            'item_name': model_name,
            'item_name_plural': model_name_plural,
            'limit': limit,
        }

        response = self.render(request, content=data)

        path = reverse('serrano:data:preview')
        links = get_page_links(request, path, page, limit, extra=params)

        return patch_response(request, response, links, {})

    # POST mimics GET to support sending large request bodies for on-the-fly
    # context and view data.
    post = get

    def delete(self, request):
        query_name = request.session.session_key
        canceled = utils.cancel_query(query_name)
        return self.render(request, {'canceled': canceled})


preview_resource = PreviewResource()

# Resource endpoints
urlpatterns = patterns(
    '',
    url(
        r'^$',
        preview_resource,
        name='preview'
    ),
    url(
        r'^(?P<page>\d+)/$',
        preview_resource,
        name='preview'
    ),
    url(
        r'^(?P<page>\d+)\.\.\.(?P<stop_page>\d+)/$',
        preview_resource,
        name='preview'
    ),
)
