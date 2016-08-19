from django.conf.urls import patterns, url
from django.http import Http404
from modeltree.tree import MODELTREE_DEFAULT_ALIAS, trees
from restlib2.params import Parametizer, IntParam, StrParam

from avocado.export import HTMLExporter
from avocado.query import pipeline, utils
from serrano.resources.base import BaseResource
from serrano.resources.processors import PREVIEW_RESULT_PROCESSOR_NAME, \
    process_results


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

    def _get_query_name(self, request):
        return request.session.session_key

    def get(self, request, **kwargs):
        params = self.get_params(request)

        # Get the request's view and context
        view = self.get_view(request)
        context = self.get_context(request)

        # Configure the query options used for retrieving the results.
        query_options = {
            'export_type': HTMLExporter.short_name,
            'query_name': self._get_query_name(request),
        }
        query_options.update(**kwargs)
        query_options.update(params)

        try:
            row_data = utils.get_result_rows(context, view, query_options,
                                             request=request)
        except ValueError:
            raise Http404

        return process_results(
            request, PREVIEW_RESULT_PROCESSOR_NAME, row_data)

    # POST mimics GET to support sending large request bodies for on-the-fly
    # context and view data.
    post = get

    def delete(self, request):
        query_name = self._get_query_name(request)
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
