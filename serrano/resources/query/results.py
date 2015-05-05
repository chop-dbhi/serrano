from django.http import Http404, HttpResponse
from restlib2.params import IntParam

from avocado.export import JSONExporter
from avocado.query import utils as query_utils
from serrano.resources.query.base import QueryBase, QueryParametizer
from ...utils import get_result_rows


class QueryResultsParametizer(QueryParametizer):
    limit = IntParam(50)


class QueryResultsResource(QueryBase):
    QUERY_NAME_TEMPLATE = 'query_result:{pk}'

    parametizer = QueryResultsParametizer

    def get_object(self, request, pk=None, session=None, **kwargs):
        if not pk and not session:
            raise ValueError('A pk or session must used for the lookup')

        if not hasattr(request, 'instance'):
            # Don't pass on page or stop_page.
            filters = dict(kwargs)
            filters.pop('page', None)
            filters.pop('stop_page', None)

            queryset = self.get_queryset(request, **filters)

            try:
                if pk:
                    instance = queryset.get(pk=pk)
                else:
                    instance = queryset.get(session=True)
            except self.model.DoesNotExist:
                instance = None

            request.instance = instance

        return request.instance

    def is_not_found(self, request, response, **kwargs):
        return self.get_object(request, **kwargs) is None

    def get(self, request, **kwargs):
        params = self.get_params(request)

        context = request.instance.context
        view = request.instance.view

        # Isolate this query to a named connection. This will cancel an
        # outstanding queries of the same name if one is present.
        query_name = self.QUERY_NAME_TEMPLATE.format(pk=request.instance.pk)

        try:
            rows, row_options = get_result_rows(
                context=context,
                view=view,
                limit=params.get('limit'),
                tree=params.get('tree'),
                processor_name=params.get('processor'),
                page=kwargs.get('page'),
                stop_page=kwargs.get('stop_page'),
                query_name=query_name,
                reader=params.get('reader'),
                export_type=JSONExporter.short_name.lower()
            )
        except ValueError:
            raise Http404

        resp = HttpResponse()
        row_options['exporter'].write(rows, buff=resp, request=request)

        return resp

    def delete(self, request, **kwargs):
        query_name = self.QUERY_NAME_TEMPLATE.format(pk=request.instance.pk)
        canceled = query_utils.cancel_query(query_name)
        return self.render(request, {'canceled': canceled})
