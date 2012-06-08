import json
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
from datetime import datetime
from django.http import HttpResponse
from django.conf.urls import patterns, url
from django.core.paginator import EmptyPage, PageNotAnInteger
from restlib2 import resources
from avocado.core.paginator import BufferedPaginator
from avocado.formatters import RawFormatter
from avocado.exporters import registry as exporters
from .dataview import DataViewResource
from .datacontext import DataContextResource

EXPORTER_MIMETYPES = ['json', 'csv', 'excel', 'r', 'sas']


class ExporterResource(resources.Resource):
    use_etags = False

    def get(self, request):
        cxt = DataContextResource.get_object(request, session=True)
        view = DataViewResource.get_object(request, session=True)

        resp = HttpResponse()

        if not cxt or not view:
            resp.status_code = 422
            resp._raw_content = {'error': 'No data can be produced, a context or view does not exist'}
            return resp

        # GET param to explicitly export the data
        export = request.GET.get('export')

        if export:
            exporter_name = export
            if exporter_name not in EXPORTER_MIMETYPES:
                resp.content = 'Format "{}" not supported. Choose one of the following: {}'.format(exporter_name, ', '.join(EXPORTER_MIMETYPES.values()))
                resp.status_code = 422
                return resp
        else:
            exporter_name = 'json+html'

        exporter_class = exporters[exporter_name]
        dataview_node = view.node()
        exporter = exporter_class(dataview_node.concepts)

        # Special case for JSON+HTML formatted especially for app consumption
        if not export:
            queryset = view.apply(cxt.apply())
            iterator = queryset[:100].raw()
            # Insert formatter to process the primary key as a raw value
            keys = [queryset.model._meta.pk.name]
            exporter.params.insert(0, (keys, 1, RawFormatter(keys=keys)))

            header = [c.name for c in dataview_node.concepts]

            rows = []
            for row in exporter.read(iterator):
                _row = []
                for output in row:
                    _row.extend(output.values())
                rows.append(_row)

            data = {
                'rows': rows,
                'header': header
            }
            resp.content = json.dumps(data)
            resp['Content-Type'] = 'application/json'
        else:
            queryset = view.apply(cxt.apply(), include_pk=False)
            iterator = queryset.raw()

            file_extension = exporter_class.file_extension
            filename = '{}-data.{}'.format(datetime.now(), exporter_class.file_extension)

            if file_extension == 'zip':
                zipball = exporter.write(iterator)
                request.content = zipball
            else:
                exporter.write(iterator, resp)

            resp['Content-Disposition'] = 'attachment; filename={}'.format(filename)

            if file_extension == 'zip':
                content_type = 'application/zip'
            elif file_extension == 'xlsx':
                content_type = 'application/vnd.ms-excel'
            elif file_extension == 'csv':
                content_type = 'text/csv'
            elif file_extension == 'json':
                content_type = 'application/json'
            else:
                content_type = 'text/plain'

            resp['Content-Type'] = content_type

        return resp


# Resource endpoints
urlpatterns = patterns('',
    url(r'^$', ExporterResource(), name='exporter'),
)