from collections import defaultdict
from decimal import Decimal
from django.conf.urls import patterns, url
from django.db import router
from django.db.models import Q
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_unicode
from restlib2 import resources, utils
from modeltree.tree import trees
from avocado.models import DataConcept
from serrano.resources.datafield import DataFieldResource

SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')

# Shortcuts defined ahead of time for transparency
can_change_dataconcept = lambda u: u.has_perm('avocado.change_dataconcept')


class DataConceptBase(resources.Resource):
    def get_queryset(self, request):
        queryset = DataConcept.objects.all()
        if not can_change_dataconcept(request.user):
            queryset = queryset.published()
        return queryset

    def get_object(self, request, **kwargs):
        queryset = self.get_queryset(request)
        try:
            return queryset.get(**kwargs)
        except DataConcept.DoesNotExist:
            pass

    def is_forbidden(self, request, response, *args, **kwargs):
        "Ensure non-privileged users cannot make any changes."
        if request.method not in SAFE_METHODS and not can_change_dataconcept(request.user):
            return True

    def is_not_found(self, request, response, pk=None, *args, **kwargs):
        if pk:
            instance = self.get_object(request, pk=pk)
            if instance is None:
                return True
            request.instance = instance
            return False


class DataConceptResource(DataConceptBase):
    "DataConcept Resource"

    template = {
        'fields': [
            ':pk', 'name', 'plural_name', 'description', 'keywords',
            'category', 'modified', 'published', 'archived', 'formatter',
            'queryview'
        ],
        'key_map': {
            'plural_name': 'get_plural_name',
        },
        'related': {
            'category': {
                'fields': [':pk', 'name', 'order', 'parent_id']
            },
        },
    }

    # Template for top-level attributes
    conceptfield_template = {
        'fields': ['alt_name', 'alt_plural_name'],
        'key_map': {
            'alt_name': 'name',
            'alt_plural_name': 'get_plural_name',
        },
    }

    @classmethod
    def serialize(self, instance):
        obj = utils.serialize(instance, **self.template)

        fields = []
        for cfield in instance.concept_fields.select_related('field').iterator():
            field = DataFieldResource.serialize(cfield.field)
            # Add the alternate name specific to the relationship between the
            # concept and the field.
            field.update(utils.serialize(cfield, **self.conceptfield_template))
            fields.append(field)

        obj['fields'] = fields
        obj['url'] = reverse('dataconcept', args=[instance.pk])
        return obj

    def get(self, request, pk=None):
        # Process GET parameters
        sort = request.GET.get('sort', None)        # default: model ordering
        direction = request.GET.get('direction', None)  # default: desc
        published = request.GET.get('published', None)
        archived = request.GET.get('archived', None)
        query = request.GET.get('query', '').strip()

        queryset = self.get_queryset(request)

        # For privileged users, check if any filters are applied
        if can_change_dataconcept(request.user):
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

        # Early exit if dealing with a single object, no need to apply sorting
        if pk:
            return self.serialize(request.instance)

        # If there is a query parameter, perform the search
        if query:
            results = DataConcept.objects.search(query, queryset)
            return map(lambda x: self.serialize(x.object), results)

        # Apply sorting
        if sort == 'name':
            if direction == 'asc':
                queryset = queryset.order_by('name')
            else:
                queryset = queryset.order_by('-name')

        return map(self.serialize, queryset.iterator())



# Resource endpoints
urlpatterns = patterns('',
    url(r'^$', DataConceptResource(), name='dataconcept'),
    url(r'^(?P<pk>\d+)/$', DataConceptResource(), name='dataconcept'),
)
