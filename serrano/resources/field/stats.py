from django.core.urlresolvers import reverse
from .base import FieldBase


class FieldStats(FieldBase):
    "Field Stats Resource"

    def get(self, request, pk):
        uri = request.build_absolute_uri
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
                'href': uri(reverse('serrano:field', args=[instance.pk])),
            },
        }

        return resp
