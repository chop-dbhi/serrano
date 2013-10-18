from serrano.resources import API_VERSION
from datetime import datetime
from django.http import HttpResponse, Http404
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from restlib2.params import Parametizer, IntParam, StrParam
from modeltree.tree import MODELTREE_DEFAULT_ALIAS, trees
from avocado.export import registry as exporters
from avocado.query import pipeline
from avocado.events import usage
from .base import BaseResource

# Single list of all registered exporters
EXPORT_TYPES = zip(*exporters.choices)[0]


class ExporterRootResource(BaseResource):
    def get(self, request):
        uri = request.build_absolute_uri

        resp = {
            'title': 'Serrano Exporter Endpoints',
            'version': API_VERSION,
            '_links': {
                'self': {
                    'href': uri(reverse('serrano:data:exporter')),
                },
            }
        }

        for export_type in EXPORT_TYPES:
            resp['_links'][export_type] = {
                'href': uri(reverse('serrano:data:exporter',
                                    kwargs={'export_type': export_type})),
                'title': exporters.get(export_type).short_name,
                'description': exporters.get(export_type).long_name,
            }
        return resp


class ExporterParametizer(Parametizer):
    limit = IntParam(50)
    tree = StrParam(MODELTREE_DEFAULT_ALIAS, choices=trees)


class ExporterResource(BaseResource):
    cache_max_age = 0

    private_cache = True

    parametizer = ExporterParametizer

    def _export(self, request, export_type, view, context, **kwargs):
        # Handle an explicit export type to a file
        resp = HttpResponse()

        params = self.get_params(request)

        limit = params.get('limit')
        tree = params.get('tree')

        page = kwargs.get('page')
        stop_page = kwargs.get('stop_page')

        offset = None

        # Restrict export to a particular page or page range
        if page:
            page = int(page)

            # Pages are 1-based
            if page < 1:
                raise Http404

            file_tag = 'p{0}'.format(page)

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
                    file_tag = 'p{0}-{1}'.format(page, stop_page)
                    limit = limit * stop_page

        else:
            # When no page or range is specified, the limit does not apply.
            limit = None
            file_tag = 'all'

        QueryProcessor = pipeline.query_processors.default
        processor = QueryProcessor(context=context, view=view, tree=tree,
                                   include_pk=False)

        exporter = processor.get_exporter(exporters[export_type])
        iterable = processor.get_iterable(offset=offset, limit=limit)

        # Write the data to the response
        exporter.write(iterable, resp, request=request)

        filename = '{0}-{1}-data.{2}'.format(
            file_tag, datetime.now(), exporter.file_extension)

        resp.set_cookie('export-type-{}'.format(
            exporter.short_name.lower()), 'complete')
        resp['Content-Disposition'] = 'attachment; filename="{0}"'.format(
            filename)
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
