from datetime import datetime
from django.http import HttpResponse
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from restlib2 import resources
from avocado.export import registry as exporters
from .base import BaseResource

# Single list of all registered exporters
EXPORT_TYPES = zip(*exporters.choices)[0]

class ExporterRootResource(resources.Resource):
    def get(self, request):
        uri = request.build_absolute_uri

        resp = {
            'title': 'Serrano Exporter Endpoints',
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


class ExporterResource(BaseResource):
    cache_max_age = 0
    private_cache = True

    def _export(self, request, export_type, view, context):
        # Handle an explicit export type to a file
        resp = HttpResponse()

        exporter_class = exporters[export_type]
        exporter = exporter_class(view)

        queryset = view.apply(context.apply(), include_pk=False)
        iterator = queryset.raw()

        file_extension = exporter.file_extension
        content_type = exporter.content_type

        filename = '{0}-data.{1}'.format(datetime.now(), file_extension)

        exporter.write(iterator, resp)

        resp['Content-Disposition'] = 'attachment; filename="{0}"'.format(filename)
        resp['Content-Type'] = content_type

        return resp

    # Resource is dependent on the available export types
    def is_not_found(self, request, response, export_type):
        return export_type not in EXPORT_TYPES

    def get(self, request, export_type):
        view = self.get_view(request)
        context = self.get_context(request)
        return self._export(request, export_type, view, context)

    post = get


exporter_resource = ExporterResource()
exporter_root_resource = ExporterRootResource()

# Resource endpoints
urlpatterns = patterns('',
    url(r'^$', exporter_root_resource, name='exporter'),
    url(r'^(?P<export_type>\w+)/$', exporter_resource, name='exporter'),
)
