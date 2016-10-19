from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from django.http import Http404
from modeltree.tree import MODELTREE_DEFAULT_ALIAS, trees
from restlib2.params import Parametizer, IntParam, StrParam

from avocado.export import BaseExporter, registry as exporters
from avocado.query import pipeline, utils
from serrano.resources import API_VERSION
from serrano.resources.base import BaseResource
from serrano.resources.processors import EXPORTER_RESULT_PROCESSOR_NAME, \
    process_results


# Single list of all registered exporters
EXPORT_TYPES = zip(*exporters.choices)[0]


class ExporterRootResource(BaseResource):
    def get_links(self, request):
        uri = request.build_absolute_uri

        links = {
            'self': uri(reverse('serrano:data:exporter')),
        }

        for export_type in EXPORT_TYPES:
            links[export_type] = {
                'link': uri(reverse(
                    'serrano:data:exporter',
                    kwargs={'export_type': export_type}
                )),
                'data': {
                    'title': exporters.get(export_type).short_name,
                    'description': exporters.get(export_type).long_name,
                }
            }

        return links

    def get(self, request):
        resp = {
            'title': 'Serrano Exporter Endpoints',
            'version': API_VERSION
        }

        return resp


class ExporterParametizer(Parametizer):
    limit = IntParam(50)
    processor = StrParam('default', choices=pipeline.query_processors)
    reader = StrParam('cached', choices=BaseExporter.readers)
    tree = StrParam(MODELTREE_DEFAULT_ALIAS, choices=trees)


class ExporterResource(BaseResource):
    cache_max_age = 0

    private_cache = True

    parametizer = ExporterParametizer

    QUERY_NAME_TEMPLATE = '{session_key}:{export_type}'

    def _get_query_name(self, request, export_type):
        return self.QUERY_NAME_TEMPLATE.format(
            session_key=request.session.session_key,
            export_type=export_type)

    # Resource is dependent on the available export types
    def is_not_found(self, request, response, export_type, **kwargs):
        return export_type not in EXPORT_TYPES

    def get(self, request, export_type, **kwargs):
        view = self.get_view(request)
        context = self.get_context(request)

        params = self.get_params(request)

        # Configure the query options used for retrieving the results.
        query_options = {
            'export_type': export_type,
            'query_name': self._get_query_name(request, export_type),
        }
        query_options.update(**kwargs)
        query_options.update(params)

        try:
            row_data = utils.get_result_rows(context, view, query_options,
                                             request=request)
        except ValueError:
            raise Http404

        return process_results(
            request, EXPORTER_RESULT_PROCESSOR_NAME, row_data)

    post = get

    def delete(self, request, export_type, **kwargs):
        query_name = self._get_query_name(request, export_type)
        canceled = utils.cancel_query(query_name)
        return self.render(request, {'canceled': canceled})


exporter_resource = ExporterResource()
exporter_root_resource = ExporterRootResource()

# Resource endpoints
urlpatterns = patterns(
    '',
    url(r'^$', exporter_root_resource, name='exporter'),
    url(r'^(?P<export_type>\w+)/$', exporter_resource, name='exporter'),
    url(r'^(?P<export_type>\w+)/(?P<page>\d+)/$', exporter_resource,
        name='exporter'),
    url(r'^(?P<export_type>\w+)/(?P<page>\d+)\.\.\.(?P<stop_page>\d+)/$',
        exporter_resource, name='exporter'),
)
