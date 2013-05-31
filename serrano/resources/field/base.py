import functools
from django.core.urlresolvers import reverse
from preserialize.serialize import serialize
from restlib2.params import Parametizer, param_cleaners
from avocado.models import DataField
from ..base import BaseResource
from .. import templates

can_change_field = lambda u: u.has_perm('avocado.change_datafield')
stats_capable = lambda x: not x.searchable and not x.internal_type == 'auto'


def field_posthook(instance, data, request):
    """Field serialization post-hook for augmenting per-instance data.

    The only two arguments the post-hook takes is instance and data. The
    remaining arguments must be partially applied using `functools.partial`
    during the request/response cycle.
    """

    uri = request.build_absolute_uri

    # Augment the links
    data['_links'] = {
        'self': {
            'href': uri(reverse('serrano:field', args=[instance.pk])),
        },
        'values': {
            'href': uri(reverse('serrano:field-values', args=[instance.pk])),
        },
    }

    if stats_capable(instance):
        data['_links']['stats'] = {
            'href': uri(reverse('serrano:field-stats', args=[instance.pk])),
        }
        data['_links']['distribution'] = {
            'href': uri(reverse('serrano:field-distribution', args=[instance.pk])),
        }

    return data


class FieldParametizer(Parametizer):
    "Supported params and their defaults for Field endpoints."

    sort = None
    order = 'asc'
    published = None
    archived = None
    brief = False
    query = ''
    limit = None

    # Not implemented
    offset = None
    page = None

    def clean_published(self, value):
        return param_cleaners.clean_bool(value)

    def clean_archived(self, value):
        return param_cleaners.clean_bool(value)

    def clean_brief(self, value):
        return param_cleaners.clean_bool(value)

    def clean_query(self, value):
        return param_cleaners.clean_string(value)

    def clean_limit(self, value):
        return param_cleaners.clean_int(value)

    def clean_offset(self, value):
        return param_cleaners.clean_int(value)

    def clean_page(self, value):
        return param_cleaners.clean_int(value)


class FieldBase(BaseResource):
    model = DataField

    parametizer = FieldParametizer

    template = templates.Field

    def get_queryset(self, request):
        queryset = self.model.objects.all()
        if not can_change_field(request.user):
            queryset = queryset.published()
        return queryset

    def get_object(self, request, **kwargs):
        queryset = self.get_queryset(request)
        try:
            return queryset.get(**kwargs)
        except self.model.DoesNotExist:
            pass

    def prepare(self, request, instance, template=None, brief=False, **params):
        if template is None:
            template = templates.BriefField if brief else self.template

        posthook = functools.partial(field_posthook, request=request)
        return serialize(instance, posthook=posthook, **template)

    def is_not_found(self, request, response, pk, *args, **kwargs):
        instance = self.get_object(request, pk=pk)
        if instance is None:
            return True
        request.instance = instance
        return False


class FieldResource(FieldBase):
    "Resource for interacting with Field instances."

    def get(self, request, pk):
        return self.prepare(request, request.instance)


class FieldsResource(FieldResource):
    "Field Collection Resource"

    def is_not_found(self, request, response, *args, **kwargs):
        return False

    def get(self, request):
        params = self.get_params(request)
        queryset = self.get_queryset(request)

        # For privileged users, check if any filters are applied, otherwise
        # only allow for published objects.
        if can_change_field(request.user):
            filters = {}

            if params['published'] is not None:
                filters['published'] = params['published']

            if params['archived'] is not None:
                filters['archived'] = params['archived']

            if filters:
                queryset = queryset.filter(**filters)
        else:
            queryset = queryset.published()

        # If Haystack is installed, perform the search
        if params['query'] and OPTIONAL_DEPS['haystack']:
            results = self.model.objects.search(params['query'],
                queryset=queryset, max_results=params['limit'])
            objects = (x.object for x in results)
        else:
            if params['sort'] == 'name':
                order = '-name' if params['order'] == 'desc' else 'name'
                queryset = queryset.order_by(order)

            if params['limit']:
                queryset = queryset[:params['limit']]

            objects = queryset

        return self.prepare(request, objects, **params)
