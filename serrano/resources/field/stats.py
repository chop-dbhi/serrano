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
            # Since the call to max() returns an Aggregator object with the
            # queryset stored internally, we don't pass the queryset to min()
            # or avg() like we do when we call max() which is called on the
            # instance itself not on an Aggregator like min() or avg() are
            # called on.
            stats = instance.max(queryset=queryset).min().avg()
        elif (instance.simple_type == 'date' or
              instance.simple_type == 'time' or
              instance.simple_type == 'datetime'):
            # Since the call to max() returns an Aggregator object with the
            # queryset stored internally, we don't pass the queryset to min()
            # like we do when we call max() which is called on the instance
            # itself not on an Aggregator like min() is called on.
            stats = instance.max(queryset=queryset).min()
        else:
            stats = instance.count(queryset=queryset, distinct=True)

        if stats is None:
            resp = {}
        else:
            try:
                resp = next(iter(stats))
            except StopIteration:
                resp = {}

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
