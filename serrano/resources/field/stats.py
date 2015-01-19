import logging
from restlib2.http import codes
from restlib2.params import Parametizer, BoolParam, StrParam
from modeltree.tree import MODELTREE_DEFAULT_ALIAS, trees
from avocado.events import usage
from avocado.query import pipeline
from serrano.conf import settings
from .base import FieldBase
from ...links import reverse_tmpl

log = logging.getLogger(__name__)


class FieldStatsParametizer(Parametizer):
    aware = BoolParam(False)
    tree = StrParam(MODELTREE_DEFAULT_ALIAS, choices=trees)
    processor = StrParam('default', choices=pipeline.query_processors)


class FieldStats(FieldBase):
    "Field Stats Resource"

    parametizer = FieldStatsParametizer

    def get_link_templates(self, request):
        uri = request.build_absolute_uri

        return {
            'self': reverse_tmpl(
                uri, 'serrano:field-stats', {'pk': (int, 'id')}),
            'parent': reverse_tmpl(
                uri, 'serrano:field', {'pk': (int, 'parent_id')}),
        }

    def get(self, request, pk):
        instance = self.get_object(request, pk=pk)

        stats_capable = settings.STATS_CAPABLE
        if stats_capable and not stats_capable(instance):
            data = {
                'message': 'This field does not support stats reporting.'
            }
            return self.render(
                request, data, status=codes.unprocessable_entity)

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

        usage.log('stats', instance=instance, request=request)
        return resp
