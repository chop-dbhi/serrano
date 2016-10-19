from django.http import Http404
from restlib2.params import IntParam

from avocado.export import JSONExporter
from avocado.query import utils as query_utils
from serrano.resources.query.base import QueryBase, QueryParametizer
from serrano.resources.processors import process_results, \
    QUERY_RESULT_PROCESSOR_NAME


class QueryResultsParametizer(QueryParametizer):
    limit = IntParam(50)


class QueryResultsResource(QueryBase):
    QUERY_NAME_TEMPLATE = 'query_result:{pk}'

    parametizer = QueryResultsParametizer

    def _get_query_name(self, request):
        return self.QUERY_NAME_TEMPLATE.format(pk=request.instance.pk)

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

        # Configure the query options used for retrieving the results.
        query_options = {
            'export_type': JSONExporter.short_name.lower(),
            'query_name': self._get_query_name(request),
        }
        query_options.update(**kwargs)
        query_options.update(params)

        try:
            row_data = query_utils.get_result_rows(
                request.instance.context,
                request.instance.view,
                query_options,
                request=request)
        except ValueError:
            raise Http404

        return process_results(
            request, QUERY_RESULT_PROCESSOR_NAME, row_data)

    def delete(self, request, **kwargs):
        query_name = self._get_query_name(request)
        canceled = query_utils.cancel_query(query_name)
        return self.render(request, {'canceled': canceled})
