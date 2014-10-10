import logging
from django.core.urlresolvers import reverse
from restlib2.params import Parametizer, BoolParam, StrParam
from avocado.events import usage
from avocado.query import pipeline
from .base import FieldBase


log = logging.getLogger(__name__)


class FieldStatsParametizer(Parametizer):
    aware = BoolParam(False)
    processor = StrParam('default', choices=pipeline.query_processors)


class FieldStats(FieldBase):
    "Field Stats Resource"

    parametizer = FieldStatsParametizer

    def get(self, request, pk):
        uri = request.build_absolute_uri
        instance = self.get_object(request, pk=pk)

        params = self.get_params(request)

        if params['aware']:
            context = self.get_context(request)
        else:
            context = None

        QueryProcessor = pipeline.query_processors[params['processor']]
        processor = QueryProcessor(context=context, tree=instance.model)
        queryset = processor.get_queryset(request=request)

        if instance.simple_type == 'number':
            resp = {
                'max': instance.max(queryset=queryset),
                'min': instance.min(queryset=queryset),
                'avg': instance.avg(queryset=queryset)
            }
        elif (instance.simple_type == 'date' or
              instance.simple_type == 'time' or
              instance.simple_type == 'datetime'):
            resp = {
                'max': instance.max(queryset=queryset),
                'min': instance.min(queryset=queryset)
            }
        else:
            resp = {
                'count': instance.count(queryset=queryset, distinct=True)
            }

        resp['_links'] = {
            'self': {
                'href': uri(
                    reverse('serrano:field-stats', args=[instance.pk])),
            },
            'parent': {
                'href': uri(reverse('serrano:field', args=[instance.pk])),
            },
        }

        usage.log('stats', instance=instance, request=request)
        return resp
