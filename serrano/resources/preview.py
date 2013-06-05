import json
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
from django.conf.urls import patterns, url
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from avocado.core.paginator import BufferedPaginator
from avocado.formatters import RawFormatter
from avocado.export import HTMLExporter
from restlib2.params import Parametizer, param_cleaners
from .base import BaseResource


class PreviewParametizer(Parametizer):
    page = 1
    per_page = 50

    def clean_page(self, value):
        return param_cleaners.clean_int(value)

    def clean_per_page(self, value):
        return param_cleaners.clean_int(value)


class PreviewResource(BaseResource):
    """Resource for *previewing* data prior to exporting.

    Data is formatted using a JSON+HTML exporter which prefers HTML formatted
    or plain strings. Browser-based clients can consume the JSON and render
    the HTML for previewing.
    """
    parametizer = PreviewParametizer

    def get(self, request):
        uri = request.build_absolute_uri

        params = self.get_params(request)

        page = params.get('page')
        per_page = params.get('per_page')

        view = self.get_view(request)
        context = self.get_context(request)

        # Apply the view to the queryset. This was not applied before since
        # the distinct count may have been computed if this was a new context.
        # Include the primary key in this case since these objects a parsed
        # and dealt with programmatically downstream (due to the pagination)
        queryset = view.apply(context.apply())

        # Standard pagination components. A buffered paginator is used
        # here which takes a pre-computed count to same a bit of performance.
        # Otherwise the Paginator class itself would execute a count on
        # initialization.
        paginator = BufferedPaginator(queryset.count(), per_page=per_page)

        try:
            page = paginator.page(page)
        except PageNotAnInteger:
            page = paginator.page(1)
        except EmptyPage:
            page = paginator.page(paginator.num_pages)

        # Get the current offset
        offset = page.offset()

        # Slice and prepare as a raw query (note: this is a
        # ModelTreeQuerySet method and is not built-in to Django)
        iterator = queryset[offset:offset + per_page].raw()

        # Apply the view to the exporter class to get the formatted output
        exporter = HTMLExporter(view)

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
        view_node = view.parse()
        ordering = OrderedDict(view_node.ordering)

        for concept in view_node.columns:
            obj = {'id': concept.id, 'name': concept.name}
            if concept.id in ordering:
                obj['direction'] = ordering[concept.id]
            header.append(obj)

        objects = []
        for row in exporter.read(iterator, request=request):
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
            'per_page': paginator.per_page,
            'num_pages': paginator.num_pages,
            'page_num': page.number,
        }

        # Augment previous and next page links if other pages exist
        links = {
            'self': {
                'href': uri(reverse('serrano:data:preview') + '?page=' +
                    str(page.number)),
            },
            'base': {
                'href': uri(reverse('serrano:data:preview')),
            }
        }

        if page.number != 1:
            links['prev'] = {
                'href': uri(reverse('serrano:data:preview') + '?page=' +
                    str(page.number - 1)),
            }

        if page.number < paginator.num_pages - 1:
            links['next'] = {
                'href': uri(reverse('serrano:data:preview') + '?page=' +
                    str(page.number + 1)),
            }

        data['_links'] = links

        return data

    post = get


preview_resource = PreviewResource()

# Resource endpoints
urlpatterns = patterns('',
    url(r'^$', preview_resource, name='preview'),
)
