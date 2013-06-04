from datetime import datetime
from django.http import HttpResponse, Http404
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from restlib2 import resources
from restlib2.params import Parametizer, param_cleaners
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


class ExporterParametizer(Parametizer):
    per_page = 50

    def clean_per_page(self, value):
        return param_cleaners.clean_int(value)


class ExporterResource(BaseResource):
    cache_max_age = 0

    private_cache = True

    parametizer = ExporterParametizer

    def _export(self, request, export_type, view, context, **kwargs):
        # Handle an explicit export type to a file
        resp = HttpResponse()

        params = self.get_params(request)
        per_page = params.get('per_page')

        exporter_class = exporters[export_type]
        exporter = exporter_class(view)

        file_extension = exporter.file_extension

        queryset = view.apply(context.apply(), include_pk=False)

        # Restrict export to a particular page or page range
        if 'page' in kwargs:
            page = int(kwargs['page'])

            # params are 1-based
            if page < 1:
                raise Http404

            file_tag = 'p{0}'.format(page)

            # change to 0-base
            offset = per_page * (page - 1)
            stop = offset + per_page

            if 'page_stop' in kwargs:
                page_stop = int(kwargs['page_stop'])

                # cannot have a lower index than page
                if page_stop < page:
                    raise Http404

                # 4...5 means 4 and 5, not everything up to 5 like with
                # list slices, so 4...4 is equivalent to just 4
                if page_stop > page:
                    file_tag = 'p{0}-{1}'.format(page, page_stop)
                    stop = offset + per_page * page_stop

            iterator = queryset[offset:stop].raw()
        else:
            file_tag = 'all'
            iterator = queryset.raw()

        filename = '{0}-{1}-data.{2}'.format(file_tag, datetime.now(),
            file_extension)

        exporter.write(iterator, resp)

        resp['Content-Disposition'] = 'attachment; filename="{0}"'.format(filename)
        resp['Content-Type'] = exporter.content_type

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
urlpatterns = patterns('',
    url(r'^$', exporter_root_resource, name='exporter'),
    url(r'^(?P<export_type>\w+)/$', exporter_resource, name='exporter'),
    url(r'^(?P<export_type>\w+)/(?P<page>\d+)/$', exporter_resource, name='exporter'),
    url(r'^(?P<export_type>\w+)/(?P<page>\d+)\.\.\.(?P<page_stop>\d+)/$', exporter_resource, name='exporter'),
)
