import json
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
from datetime import datetime
from django.http import HttpResponse
from django.conf.urls import patterns, url
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from restlib2.http import codes
from avocado.core.paginator import BufferedPaginator
from avocado.formatters import RawFormatter
from avocado.export import JSONExporter, registry as exporters
from .base import BaseResource

# Single list of all registered exporters
EXPORT_TYPES = zip(*exporters.choices)[0]


# Special exporter for JSON+HTML output for browser-based clients
class JSONHTMLExporter(JSONExporter):
    preferred_formats = ('html', 'string')


class ExporterResource(BaseResource):
    cache_max_age = 0
    private_cache = True

    param_defaults = {
        'page': 1,
        'per_page': 10,
    }

    def get(self, request):
        params = self.get_params(request)

        # GET param to explicitly export the data
        export_type = params.get('export')

        # Attempt to get the appropriate view and context objects
        view = self.get_view(request)
        context = self.get_context(request)

        view_node = view.node()

        # Special case for browser-based consumption
        if not export_type:
            exporter_class = JSONHTMLExporter
            exporter = exporter_class(view_node.columns)

            page = params.get('page')
            try:
                per_page = int(params.get('per_page'))
            except (ValueError, TypeError):
                per_page = self.param_defaults['per_page']

            # For new contexts, `count` will be `None`
            if context.count is None:
                context.count = context.apply().distinct().count()
                context.save()

            paginator = BufferedPaginator(context.count, per_page=per_page)

            try:
                page = paginator.page(page)
            except PageNotAnInteger:
                page = paginator.page(1)
            except EmptyPage:
                page = paginator.page(paginator.num_pages)

            # Get the current offset
            offset = page.offset()

            # Build the queryset
            queryset = view.apply(context.apply()).distinct()

            # Slice and prepare as a raw query (note: this is a
            # ModelTreeQuerySet method and is not built-in to Django)
            iterator = queryset[offset:offset + per_page].raw()

            # Insert formatter to process the primary key as a raw value
            pk_name = queryset.model._meta.pk.name
            exporter.params.insert(0, (RawFormatter(keys=[pk_name]), 1))

            # Build up the header values
            header = []

            ordering = OrderedDict(view_node.ordering)

            for concept in view_node.columns:
                obj = {'id': concept.id, 'name': concept.name}
                if concept.id in ordering:
                    obj['direction'] = ordering[concept.id]
                header.append(obj)

            objects = []
            for row in exporter.read(iterator):
                pk = None
                values = []
                for i, output in enumerate(row):
                    if i == 0:
                        pk = output[pk_name]
                    else:
                        values.extend(output.values())
                objects.append({'pk': pk, 'values': values})

            # Various other attributes about the model
            model_meta = queryset.model._meta
            model_name = model_meta.verbose_name.format()
            model_name_plural = model_meta.verbose_name_plural.format()

            data = {
                'keys': header,
                'objects': objects,
                'object_name': model_name,
                'object_name_plural': model_name_plural,
                'num_pages': paginator.num_pages,
                'page_num': page.number,
            }

            # Augment previous and next page links if other pages exist
            links = {
                'self': {
                    'rel': 'self',
                    'href': reverse('serrano:exporter') + '?page=' + \
                        str(page.number),
                },
                'base': {
                    'rel': 'base',
                    'href': reverse('serrano:exporter'),
                }
            }

            if page.number != 1:
                links['prev'] = {
                    'rel': 'prev',
                    'href': reverse('serrano:exporter') + '?page=' + \
                        str(page.number - 1),
                }
            if page.number < paginator.num_pages - 1:
                links['next'] = {
                    'rel': 'next',
                    'href': reverse('serrano:exporter') + '?page=' + \
                        str(page.number + 1),
                }
            data['_links'] = links
            return HttpResponse(json.dumps(data), content_type='application/json')

        # Handle an explicit export type to a file
        resp = HttpResponse()

        if export_type not in EXPORT_TYPES:
            types = ', '.join(EXPORT_TYPES)
            resp.content = "Export type '{}' is not supported. Choose one " \
                "of the following: {}".format(export_type, types)
            resp.status_code = codes.unprocessable_entity
            return resp

        exporter_class = exporters[export_type]
        exporter = exporter_class(view_node.columns)

        queryset = view.apply(context.apply(), include_pk=False).distinct()
        iterator = queryset.raw()

        file_extension = exporter_class.file_extension
        filename = '{}-data.{}'.format(datetime.now(),
            exporter_class.file_extension)

        if file_extension == 'zip':
            zipball = exporter.write(iterator)
            request.content = zipball
        else:
            exporter.write(iterator, resp)

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

        resp['Content-Disposition'] = 'attachment; filename={}'.format(filename)
        resp['Content-Type'] = content_type

        return resp


exporter_resource = ExporterResource()


# Resource endpoints
urlpatterns = patterns('',
    url(r'^$', exporter_resource, name='exporter'),
)
