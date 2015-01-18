from django.utils.encoding import smart_unicode
from restlib2.http import codes
from restlib2.params import Parametizer, StrParam, BoolParam
from modeltree.tree import MODELTREE_DEFAULT_ALIAS, trees
from avocado.events import usage
from avocado.query import pipeline
from .base import FieldBase, is_field_orphaned


class FieldDistParametizer(Parametizer):
    aware = BoolParam(False)
    tree = StrParam(MODELTREE_DEFAULT_ALIAS, choices=trees)
    processor = StrParam('default', choices=pipeline.query_processors)


class FieldDistribution(FieldBase):
    "Field Counts Resource"

    parametizer = FieldDistParametizer

    def get(self, request, pk):
        instance = self.get_object(request, pk=pk)

        if is_field_orphaned(instance):
            data = {
                'message': 'Orphaned fields do not support distribution calls.'
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

        # Get the value/label mapping to augment the result for display
        value_labels = instance.value_labels(queryset=queryset)

        result = []

        for value, count in instance.dist(queryset=queryset):
            if value in value_labels:
                label = value_labels[value]
            else:
                label = smart_unicode(value)

            result.append({
                'value': value,
                'label': label,
                'count': count,
            })

        usage.log('dist', instance=instance, request=request)

        return result
