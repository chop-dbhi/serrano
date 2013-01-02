from django.core.urlresolvers import reverse
from preserialize.serialize import serialize
from avocado.models import DataField
from avocado.conf import OPTIONAL_DEPS
from ..base import BaseResource
from .. import templates

# Shortcuts defined ahead of time for transparency
can_change_datafield = lambda u: u.has_perm('avocado.change_datafield')

stats_capable = lambda x: not x.searchable and not x.internal_type == 'auto'


class DataFieldBase(BaseResource):
    template = templates.DataField

    param_defaults = {
        'query': '',
    }

    def get_queryset(self, request):
        queryset = DataField.objects.all()
        if not can_change_datafield(request.user):
            queryset = queryset.published()
        return queryset

    def get_object(self, request, **kwargs):
        queryset = self.get_queryset(request)
        try:
            return queryset.get(**kwargs)
        except DataField.DoesNotExist:
            pass

    # Augment the pre-serialized object
    @classmethod
    def prepare(self, instance):
        obj = serialize(instance, **self.template)

        # Augment the links
        obj['_links'] = {
            'self': {
                'rel': 'self',
                'href': reverse('serrano:datafield', args=[instance.pk]),
            },
            'values': {
                'rel': 'data',
                'href': reverse('serrano:datafield-values', args=[instance.pk]),
            },
        }

        if stats_capable(instance):
            obj['_links']['stats'] = {
                'rel': 'data',
                'href': reverse('serrano:datafield-stats', args=[instance.pk]),
            }
            # Add distribution link only if the relevent dependencies are
            # installed.
            if OPTIONAL_DEPS['scipy']:
                obj['_links']['distribution'] = {
                    'rel': 'data',
                    'href': reverse('serrano:datafield-distribution', args=[instance.pk]),
                }

        return obj

    def is_not_found(self, request, response, pk, *args, **kwargs):
        instance = self.get_object(request, pk=pk)
        if instance is None:
            return True
        request.instance = instance
        return False



class DataFieldResource(DataFieldBase):
    "DataField Resource"
    def get(self, request, pk):
        return self.prepare(request.instance)


class DataFieldsResource(DataFieldResource):
    "DataField Collection Resource"

    def is_not_found(self, request, response, *args, **kwargs):
        return False

    def get(self, request):
        params = self.get_params(request)

        # Process GET parameters
        sort = params.get('sort')               # default: model ordering
        direction = params.get('direction')     # default: desc
        published = params.get('published')
        archived = params.get('archived')

        # This is only application if Haystack is setup
        if OPTIONAL_DEPS['haystack']:
            query = params.get('query').strip()
        else:
            query = ''

        queryset = self.get_queryset(request)

        # For privileged users, check if any filters are applied
        if can_change_datafield(request.user):
            filters = {}

            if published == 'true':
                filters['published'] = True
            elif published == 'false':
                filters['published'] = False

            if archived == 'true':
                filters['archived'] = True
            elif archived == 'false':
                filters['archived'] = False

            if filters:
                queryset = queryset.filter(**filters)

        # For non-privileged users, filter out the non-published and archived
        else:
            queryset = queryset.published()

        # If there is a query parameter, perform the search
        if query:
            results = DataField.objects.search(query, queryset)
            objects = map(lambda x: x.object, results)
        else:
            # Apply sorting
            if sort == 'name':
                if direction == 'asc':
                    queryset = queryset.order_by('name')
                else:
                    queryset = queryset.order_by('-name')
            objects = queryset.iterator()

        return map(self.prepare, objects)
