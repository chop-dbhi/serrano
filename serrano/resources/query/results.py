from django.http import Http404, HttpResponse
from restlib2.params import IntParam

from avocado.export import JSONExporter
from avocado.query import pipeline, utils as query_utils
from serrano.resources.query.base import QueryBase, QueryParametizer


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
        context = request.instance.context
        view = request.instance.view

        params = self.get_params(request)

        limit = params.get('limit')
        tree = params.get('tree')

        page = kwargs.get('page')
        stop_page = kwargs.get('stop_page')

        offset = None

        if page:
            page = int(page)

            # Pages are 1-based.
            if page < 1:
                raise Http404

            # Change to 0-base for calculating offset.
            offset = limit * (page - 1)

            if stop_page:
                stop_page = int(stop_page)

                # Cannot have a lower index stop page than start page.
                if stop_page < page:
                    raise Http404

                # 4...5 means 4 and 5, not everything up to 5 like with
                # list slices, so 4...4 is equivalent to just 4
                if stop_page > page:
                    limit = limit * stop_page
        else:
            # When no page or range is specified, the limit does not apply.
            limit = None

        QueryProcessor = pipeline.query_processors[params['processor']]
        processor = QueryProcessor(context=context, view=view, tree=tree)
        queryset = processor.get_queryset(request=request)

        # Isolate this query to a named connection. This will cancel an
        # outstanding queries of the same name if one is present.
        query_name = self.QUERY_NAME_TEMPLATE.format(pk=request.instance.pk)
        query_utils.cancel_query(query_name)
        queryset = query_utils.isolate_queryset(query_name, queryset)

        exporter = processor.get_exporter(JSONExporter)

        # This is an optimization when concepts are selected for ordering
        # only. There is not guarantee to how many rows are required to get
        # the desired `limit` of rows, so the query is unbounded. If all
        # ordering facets are visible, the limit and offset can be pushed
        # down to the query.
        order_only = lambda f: not f.get('visible', True)
        view_node = view.parse()
        resp = HttpResponse()

        if filter(order_only, view_node.facets):
            iterable = processor.get_iterable(queryset=queryset,
                                              request=request)

            # Write the data to the response
            exporter.write(iterable,
                           resp,
                           request=request,
                           offset=offset,
                           limit=limit)
        else:
            iterable = processor.get_iterable(queryset=queryset,
                                              request=request,
                                              limit=limit,
                                              offset=offset)

            exporter.write(iterable,
                           resp,
                           request=request)

        return resp

    def delete(self, request, **kwargs):
        query_name = self.QUERY_NAME_TEMPLATE.format(pk=request.instance.pk)
        canceled = query_utils.cancel_query(query_name)
        return self.render(request, {'canceled': canceled})
