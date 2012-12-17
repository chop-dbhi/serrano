import json
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
from django.http import HttpResponse
from django.conf.urls import patterns, url
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.core.serializers.json import DjangoJSONEncoder
from avocado.core.paginator import BufferedPaginator
from avocado.formatters import RawFormatter
from avocado.export import HTMLExporter
from .base import BaseResource


class PreviewResource(BaseResource):
    """Resource for *previewing* data prior to exporting.

    Data is formatted using a JSON+HTML exporter which prefers HTML formatted
    or plain strings. Browser-based clients can consume the JSON and render
    the HTML for previewing.
    """
    param_detaults = {
        'page': 1,
        'per_page': 50,
    }

    def get(self, request):
        params = self.get_params(request)

        page = params.get('page')
        per_page = params.get('per_page')

        view = self.get_view(request)
        context = self.get_context(request)

        try:
            per_page = int(per_page)
        except (ValueError, TypeError):
            per_page = self.param_defaults.get('per_page')

        # Create the queryset based off the context. Note, this does not
        # take a `tree` param to customize the root model.
        queryset = context.apply().distinct()

        # For new contexts, `count` will be `None`
        if context.count is None:
            context.count = queryset.count()
            context.save()

        # Standard pagination components. A buffered paginator is used
        # here which takes a pre-computed count to same a bit of performance.
        # Otherwise the Paginator class itself would execute a count on
        # initialization.
        paginator = BufferedPaginator(context.count, per_page=per_page)

        try:
            page = paginator.page(page)
        except PageNotAnInteger:
            page = paginator.page(1)
        except EmptyPage:
            page = paginator.page(paginator.num_pages)

        # Get the current offset
        offset = page.offset()

        # Apply the view to the queryset. This was not applied before since
        # the distinct count may have been computed if this was a new context.
        # Include the primary key in this case since these objects a parsed
        # and dealt with programmatically downstream (due to the pagination)
        queryset = view.apply(queryset)

        # Slice and prepare as a raw query (note: this is a
        # ModelTreeQuerySet method and is not built-in to Django)
        iterator = queryset[offset:offset + per_page].raw()

        # Apply the view to the exporter class to get the formatted output
        view_node = view.parse()
        exporter = HTMLExporter(view_node.columns)

        # Insert formatter to process the primary key as a raw value
        # TODO: this is not terribly elegant
        pk_name = queryset.model._meta.pk.name
        exporter.params.insert(0, (RawFormatter(keys=[pk_name]), 1))
        exporter.row_length += 1

        # Build up the header keys.
        # TODO: This is flawed since it assumes the output columns
        # of exporter will be one-to-one with the concepts. This should
        # be built during the first iteration of the read, but would also
        # depend on data to exist!
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

        # Various other model options
        opts = queryset.model._meta
        model_name = opts.verbose_name.format()
        model_name_plural = opts.verbose_name_plural.format()

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
                'href': reverse('serrano:data:preview') + '?page=' + \
                    str(page.number),
            },
            'base': {
                'rel': 'base',
                'href': reverse('serrano:data:preview'),
            }
        }

        if page.number != 1:
            links['prev'] = {
                'rel': 'prev',
                'href': reverse('serrano:data:preview') + '?page=' + \
                    str(page.number - 1),
            }

        if page.number < paginator.num_pages - 1:
            links['next'] = {
                'rel': 'next',
                'href': reverse('serrano:data:preview') + '?page=' + \
                    str(page.number + 1),
            }

        data['_links'] = links

        return HttpResponse(json.dumps(data, cls=DjangoJSONEncoder),
            content_type='application/json')

    post = get


preview_resource = PreviewResource()

# Resource endpoints
urlpatterns = patterns('',
    url(r'^$', preview_resource, name='preview'),
)
