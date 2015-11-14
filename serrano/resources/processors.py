try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
from datetime import datetime

from django.core.urlresolvers import reverse
from django.http import HttpResponse
from restlib2.serializers import serializers

from avocado.events import usage
from avocado.query.utils import get_exporter_class
from serrano.conf import settings
from serrano.links import patch_response


ASYNC_EXPORTER_RESULT_PROCESSOR_NAME = 'async_exporter'
ASYNC_PREVIEW_RESULT_PROCESSOR_NAME = 'async_preview'
ASYNC_QUERY_RESULT_PROCESSOR_NAME = 'async_query'

EXPORTER_RESULT_PROCESSOR_NAME = 'exporter'
PREVIEW_RESULT_PROCESSOR_NAME = 'preview'
QUERY_RESULT_PROCESSOR_NAME = 'query'


class BaseResultProcessor(object):
    name = 'default'

    def process(self, request, result_data):
        exporter = result_data['processor'].get_exporter(
            get_exporter_class(result_data['export_type']))
        resp = HttpResponse(content_type=exporter.content_type)
        exporter.write(result_data['rows'], buff=resp, request=request)
        return resp


class ExporterResultProcessor(BaseResultProcessor):
    name = EXPORTER_RESULT_PROCESSOR_NAME

    def process(self, request, result_data):
        export_type = result_data['export_type']
        exporter = result_data['processor'].get_exporter(
            get_exporter_class(export_type))
        page = result_data['page']
        stop_page = result_data['stop_page']

        # Build a file name for the export file based on the page range.
        if page:
            file_tag = 'p{0}'.format(page)

            if stop_page and stop_page > page:
                file_tag = 'p{0}-{1}'.format(page, stop_page)
        else:
            file_tag = 'all'

        resp = HttpResponse()
        exporter.write(result_data['rows'], buff=resp, request=request)

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


class PreviewResultProcessor(BaseResultProcessor):
    name = PREVIEW_RESULT_PROCESSOR_NAME
    reverse_name = 'serrano:data:preview'

    def get_page_links(self, request, path, page, limit, extra=None):
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

    def process(self, request, result_data):
        objects = []

        # Split the primary key from the requested values in the row.
        for row in result_data['rows']:
            objects.append({
                'pk': row[0],
                'values': row[1:],
            })

        header = []
        exporter = result_data['processor'].get_exporter(
            get_exporter_class(result_data['export_type']))
        view_node = result_data['view'].parse()
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
        opts = result_data['queryset'].model._meta

        model_name = opts.verbose_name.format()
        model_name_plural = opts.verbose_name_plural.format()

        data = {
            'keys': header,
            'items': objects,
            'item_name': model_name,
            'item_name_plural': model_name_plural,
            'limit': result_data['limit'],
            'page': result_data['page'],
        }

        response = HttpResponse(
            content=serializers.encode('application/json', data),
            content_type='application/json')

        path = reverse(self.reverse_name)
        links = self.get_page_links(
            request, path, result_data['page'], result_data['limit'])

        return patch_response(request, response, links, {})


class QueryResultProcessor(BaseResultProcessor):
    name = QUERY_RESULT_PROCESSOR_NAME


class AsyncExporterResultProcessor(ExporterResultProcessor):
    name = ASYNC_EXPORTER_RESULT_PROCESSOR_NAME
    reverse_name = 'serrano:async:exporter'


class AsyncPreviewResultProcessor(PreviewResultProcessor):
    name = ASYNC_PREVIEW_RESULT_PROCESSOR_NAME
    reverse_name = 'serrano:async:preview'


class AsyncQueryResultProcessor(QueryResultProcessor):
    name = ASYNC_QUERY_RESULT_PROCESSOR_NAME
    reverse_name = 'serrano:async:query'


RESULT_PROCESSORS = {
    ASYNC_EXPORTER_RESULT_PROCESSOR_NAME: AsyncExporterResultProcessor(),
    ASYNC_PREVIEW_RESULT_PROCESSOR_NAME: AsyncPreviewResultProcessor(),
    ASYNC_QUERY_RESULT_PROCESSOR_NAME: AsyncQueryResultProcessor(),
    EXPORTER_RESULT_PROCESSOR_NAME: ExporterResultProcessor(),
    PREVIEW_RESULT_PROCESSOR_NAME: PreviewResultProcessor(),
    QUERY_RESULT_PROCESSOR_NAME: QueryResultProcessor(),
}


def process_results(request, result_type, result_data):
    if result_type in RESULT_PROCESSORS:
        return RESULT_PROCESSORS[result_type].process(request, result_data)
    else:
        return BaseResultProcessor.process(request, result_data)
