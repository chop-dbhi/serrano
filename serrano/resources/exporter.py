import json
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
from datetime import datetime
from django.http import HttpResponse
from django.conf.urls import patterns, url
from django.core.paginator import EmptyPage, PageNotAnInteger
from avocado.core.paginator import BufferedPaginator
from avocado.formatters import RawFormatter
from avocado.export import registry as exporters
from .base import BaseResource

EXPORTER_MIMETYPES = ['json', 'csv', 'excel', 'r', 'sas']


class ExporterResource(BaseResource):
    use_etags = False

    def get(self, request):
        params = self.get_params(request)

        context = self.get_context(request)
        view = self.get_view(request)

        resp = HttpResponse()

        if not context or not view:
            return {
                'rows': [],
                'header': [],
                'num_pages': 0,
                'page_num': 1,
            }

        # GET param to explicitly export the data
        export = params.get('export')

        if export:
            exporter_name = export
            if exporter_name not in EXPORTER_MIMETYPES:
                resp.content = "Format '{}' not supported. Choose one of the following: {}".format(exporter_name, ', '.join(EXPORTER_MIMETYPES.values()))
                resp.status_code = 422
                return resp
        else:
            exporter_name = 'json+html'

        exporter_class = exporters[exporter_name]
        dataview_node = view.node()
        exporter = exporter_class(dataview_node.concepts)

        # Special case for JSON+HTML formatted especially for app consumption
        if not export:
            page = request.GET.get('page')
            per_page = 50
            paginator = BufferedPaginator(context.count, per_page=per_page)

            try:
                page = paginator.page(page)
            except PageNotAnInteger:
                page = paginator.page(1)
            except EmptyPage:
                page = paginator.page(paginator.num_pages)

            offset = page.offset()
            queryset = view.apply(context.apply()).distinct()
            iterator = queryset[offset:offset + per_page].raw()
            # Insert formatter to process the primary key as a raw value
            keys = [queryset.model._meta.pk.name]
            exporter.params.insert(0, (keys, 1, RawFormatter(keys=keys)))

            header = []
            for concept in dataview_node.concepts:
                obj = {'id': concept.id, 'name': concept.name}
                ordering = filter(lambda x: x[0] == obj['id'], dataview_node.ordering)
                if ordering:
                    obj['direction'] = ordering[0][1]
                header.append(obj)

            rows = []
            for row in exporter.read(iterator):
                _row = []
                for output in row:
                    _row.extend(output.values())
                rows.append(_row)

            data = {
                'rows': rows,
                'header': header,
                'num_pages': paginator.num_pages,
                'page_num': page.number,
            }
            resp.content = json.dumps(data)
            resp['Content-Type'] = 'application/json'
        else:
            queryset = view.apply(context.apply(), include_pk=False).distinct()
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
