try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from django.http import Http404
from modeltree.tree import MODELTREE_DEFAULT_ALIAS, trees
from restlib2.params import Parametizer, IntParam, StrParam
from avocado.export import HTMLExporter
from avocado.query import pipeline, utils
from .base import BaseResource
from ..links import patch_response
from ..utils import get_result_rows


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

        # Get the request's view and context
        view = self.get_view(request)
        context = self.get_context(request)

        try:
            rows, row_options = get_result_rows(
                context,
                view,
                params.get('limit'),
                params.get('tree'),
                params.get('processor'),
                kwargs.get('page'),
                kwargs.get('stop_page'),
                request.session.session_key,
                params.get('reader'),
                HTMLExporter.short_name
            )
        except ValueError:
            raise Http404

        objects = []

        # Split the primary key from the requested values in the row.
        for row in rows:
            objects.append({
                'pk': row[0],
                'values': row[1:],
            })

        header = []
        view_node = view.parse()
        concepts = view_node.get_concepts_for_select()
        ordering = OrderedDict(view_node.ordering)

        # Skip the primary key field in the header since it is not exposed
        # in the row output below.
        for i, f in enumerate(row_options['exporter'].header[1:]):
            concept = concepts[i]

            obj = {
                'id': concept.id,
                'name': f['label'],
            }

            if concept.id in ordering:
                obj['direction'] = ordering[concept.id]

            header.append(obj)

        # Various model options
        opts = row_options['queryset'].model._meta

        model_name = opts.verbose_name.format()
        model_name_plural = opts.verbose_name_plural.format()

        data = {
            'keys': header,
            'items': objects,
            'item_name': model_name,
            'item_name_plural': model_name_plural,
            'limit': row_options['limit'],
        }

        response = self.render(request, content=data)

        path = reverse('serrano:data:preview')
        links = get_page_links(request, path, row_options['page'],
                               row_options['limit'], extra=params)

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
