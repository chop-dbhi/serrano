from avocado.query import pipeline
from serrano.resources.query.base import QueryBase


class QueryStatsResource(QueryBase):
    def is_not_found(self, request, response, **kwargs):
        return self.get_object(request, **kwargs) is None

    def get(self, request, **kwargs):
        params = self.get_params(request)
        instance = self.get_object(request, **kwargs)

        QueryProcessor = pipeline.query_processors[params['processor']]
        processor = QueryProcessor(tree=params['tree'])
        queryset = processor.get_queryset(request=request)

        return {
            'distinct_count': instance.context.count(queryset=queryset),
            'record_count': instance.count(queryset=queryset)
        }
