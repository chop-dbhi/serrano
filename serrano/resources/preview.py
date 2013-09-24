try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from modeltree.tree import MODELTREE_DEFAULT_ALIAS, trees
from avocado.query import pipeline
from avocado.export import HTMLExporter
from restlib2.params import StrParam
from .base import BaseResource
from .pagination import PaginatorResource, PaginatorParametizer


class PreviewParametizer(PaginatorParametizer):
    tree = StrParam(MODELTREE_DEFAULT_ALIAS, choices=trees)


class PreviewResource(BaseResource, PaginatorResource):
    """Resource for *previewing* data prior to exporting.

    Data is formatted using a JSON+HTML exporter which prefers HTML formatted
    or plain strings. Browser-based clients can consume the JSON and render
    the HTML for previewing.
    """

    parametizer = PreviewParametizer

    def get(self, request):
        params = self.get_params(request)

        page = params.get('page')
        limit = params.get('limit')
        tree = params.get('tree')

        # Get the request's view and context
        view = self.get_view(request)
        context = self.get_context(request)

        # Initialize a query processor
        QueryProcessor = pipeline.query_processors.default
        processor = QueryProcessor(context=context, view=view, tree=tree)

        # Build a queryset for pagination and other downstream use
        queryset = processor.get_queryset(request=request)

        # Get paginator and page
        paginator = self.get_paginator(queryset, limit=limit)
        page = paginator.page(page)
        offset = max(0, page.start_index() - 1)

        # Prepare the exporter and iterable
        iterable = processor.get_iterable(offset=offset, limit=limit)

        # Build up the header keys.
        # TODO: This is flawed since it assumes the output columns
        # of exporter will be one-to-one with the concepts. This should
        # be built during the first iteration of the read, but would also
        # depend on data to exist!
        header = []
        view_node = view.parse()
        ordering = OrderedDict(view_node.ordering)

        for concept in view_node.get_concepts_for_select():
            obj = {'id': concept.id, 'name': concept.name}
            if concept.id in ordering:
                obj['direction'] = ordering[concept.id]
            header.append(obj)

        # Prepare an HTMLExporter
        exporter = processor.get_exporter(HTMLExporter)
        pk_name = queryset.model._meta.pk.name

        objects = []

        for row in exporter.read(iterable, request=request):
            pk = None
            values = []
            for i, output in enumerate(row):
                if i == 0:
                    pk = output[pk_name]
                else:
                    values.extend(output.values())
            objects.append({'pk': pk, 'values': values})

        # Various model options
        opts = queryset.model._meta
        model_name = opts.verbose_name.format()
        model_name_plural = opts.verbose_name_plural.format()

        path = reverse('serrano:data:preview')
        links = self.get_page_links(request, path, page, extra=params)

        return {
            'keys': header,
            'objects': objects,
            'object_name': model_name,
            'object_name_plural': model_name_plural,
            'object_count': paginator.count,
            'limit': paginator.per_page,
            'num_pages': paginator.num_pages,
            'page_num': page.number,
            '_links': links,
        }

    # POST mimics GET to support sending large request bodies for on-the-fly
    # context and view data.
    post = get


preview_resource = PreviewResource()

# Resource endpoints
urlpatterns = patterns('', url(r'^$', preview_resource, name='preview'), )
