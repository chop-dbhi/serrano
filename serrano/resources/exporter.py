from datetime import datetime
from django.http import HttpResponse, Http404
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from restlib2.params import Parametizer, IntParam, StrParam
from modeltree.tree import MODELTREE_DEFAULT_ALIAS, trees
from avocado.export import BaseExporter, registry as exporters
from avocado.query import pipeline, utils
from avocado.events import usage
from ..conf import settings
from . import API_VERSION
from .base import BaseResource
from ..utils import get_result_rows


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

    def _export(self, request, export_type, view, context, **kwargs):
        params = self.get_params(request)

        # Use a separate name for each for export type.
        query_name = '{0}:{1}'.format(request.session.session_key, export_type)

        try:
            rows, row_options = get_result_rows(
                context,
                view,
                params.get('limit'),
                params.get('tree'),
                params.get('processor'),
                kwargs.get('page'),
                kwargs.get('stop_page'),
                query_name,
                params.get('reader'),
                export_type
            )
        except ValueError:
            raise Http404

        exporter = row_options['exporter']
        page = row_options['page']
        stop_page = row_options['stop_page']

        # Build a file name for the export file based on the page range.
        if page:
            file_tag = 'p{0}'.format(page)

            if stop_page and stop_page > page:
                file_tag = 'p{0}-{1}'.format(page, stop_page)
        else:
            file_tag = 'all'

        resp = HttpResponse()
        exporter.write(rows,
                       buff=resp,
                       request=request)

        filename = '{0}-{1}-data.{2}'.format(file_tag,
                                             datetime.now(),
                                             exporter.file_extension)

        cookie_name = settings.EXPORT_COOKIE_NAME_TEMPLATE.format(export_type)
        resp.set_cookie(cookie_name, settings.EXPORT_COOKIE_DATA)

        resp['Content-Disposition'] = 'attachment; filename="{0}"'\
                                      .format(filename)
        resp['Content-Type'] = exporter.content_type

        usage.log('export', request=request, data={
            'type': export_type,
            'partial': page is not None,
        })

        return resp

    # Resource is dependent on the available export types
    def is_not_found(self, request, response, export_type, **kwargs):
        return export_type not in EXPORT_TYPES

    def get(self, request, export_type, **kwargs):
        view = self.get_view(request)
        context = self.get_context(request)
        return self._export(request, export_type, view, context, **kwargs)

    post = get

    def delete(self, request, export_type, **kwargs):
        query_name = '{0}:{1}'.format(request.session.session_key, export_type)
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
