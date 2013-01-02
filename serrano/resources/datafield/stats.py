from django.core.urlresolvers import reverse
from .base import DataFieldBase


class DataFieldStats(DataFieldBase):
    "DataField Stats Resource"

    def get(self, request, pk):
        instance = request.instance

        stats = None

        if instance.simple_type == 'number':
            stats = instance.max().min().avg()
        elif instance.simple_type == 'string' and instance.enumerable:
            stats = instance.count(distinct=True)

        if stats is None:
            resp = {}
        else:
            resp = next(iter(stats))

        resp['_links'] = {
            'parent': {
                'rel': 'parent',
                'href': reverse('serrano:datafield', args=[instance.pk]),
            },
        }

        return resp
