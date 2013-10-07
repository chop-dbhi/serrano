from django.core.urlresolvers import reverse
from avocado.events import usage
from .base import FieldBase


class FieldStats(FieldBase):
    "Field Stats Resource"

    def get(self, request, pk):
        uri = request.build_absolute_uri
        instance = request.instance

        if instance.simple_type == 'number':
            stats = instance.max().min().avg()
        elif (instance.simple_type == 'date' or
              instance.simple_type == 'time' or
              instance.simple_type == 'datetime'):
            stats = instance.max().min()
        else:
            stats = instance.count(distinct=True)

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
