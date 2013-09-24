import logging
import functools
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from preserialize.serialize import serialize
from restlib2.http import codes
from restlib2.params import Parametizer, BoolParam, StrParam, IntParam
from avocado.events import usage
from avocado.models import DataConcept, DataCategory
from avocado.conf import OPTIONAL_DEPS
from serrano.resources.field import FieldResource
from .base import ThrottledResource, SAFE_METHODS
from . import templates
from .field import base as FieldResources

can_change_concept = lambda u: u.has_perm('avocado.change_dataconcept')
log = logging.getLogger(__name__)


def has_orphaned_field(instance):
    has_orphan = False
    for field in instance.fields.iterator():
        if FieldResources.is_field_orphaned(field):
            log.error('Concept has orphaned field.',
                      extra={
                          'concept': instance.pk,
                          'field': field.pk
                      })
            has_orphan = True
    return has_orphan


def concept_posthook(instance, data, request, embed, brief, categories=None):
    """Concept serialization post-hook for augmenting per-instance data.

    The only two arguments the post-hook takes is instance and data. The
    remaining arguments must be partially applied using `functools.partial`
    during the request/response cycle.
    """
    uri = request.build_absolute_uri

    if categories is None:
        categories = {}

    if 'category_id' in data:
        # This relies on categories being passed in as a dict with the key
        # being the primary key. This makes it must faster since the
        # categories are pre-cached.
        category = categories.get(data.pop('category_id'))
        data['category'] = serialize(category, **templates.Category)

        if data['category']:
            parent = categories.get(data['category'].pop('parent_id'))
            data['category']['parent'] = serialize(
                parent, **templates.Category)

            # Embed first parent as well, but no others since this is the
            # bound in Avocado's DataCategory parent field.
            if data['category']['parent']:
                data['category']['parent'].pop('parent_id')

    if not brief:
        data['_links'] = {
            'self': {
                'href': uri(reverse('serrano:concept', args=[instance.pk])),
            },
            'fields': {
                'href': uri(
                    reverse('serrano:concept-fields', args=[instance.pk])),
            }
        }

    # Embeds the related fields directly in the concept output
    if not brief and embed:
        resource = ConceptFieldsResource()
        data['fields'] = resource.prepare(request, instance)

    return data


class ConceptParametizer(Parametizer):
    "Supported params and their defaults for Concept endpoints."

    sort = StrParam()
    order = StrParam('asc')
    published = BoolParam()
    embed = BoolParam(False)
    brief = BoolParam(False)
    query = StrParam()
    limit = IntParam()


class ConceptBase(ThrottledResource):
    "Base resource for Concept-related data."

    model = DataConcept

    template = templates.Concept

    parametizer = ConceptParametizer

    def get_queryset(self, request):
        queryset = self.model.objects.all()
        if not can_change_concept(request.user):
            queryset = queryset.published()
        return queryset

    def get_object(self, request, **kwargs):
        queryset = self.get_queryset(request)
        try:
            return queryset.get(**kwargs)
        except self.model.DoesNotExist:
            pass

    def _get_categories(self, request, objects):
        """Returns a QuerySet of categories for use during serialization.

        Since `category` is a nullable relationship to `concept`, a lookup
        would have to occur for every concept being serialized. This returns
        a QuerySet applicable to the resource using it and is cached for the
        remainder of the request/response cycle.
        """
        return dict((x.pk, x) for x in list(DataCategory.objects.all()))

    def prepare(self, request, objects, template=None, embed=False,
                brief=False, **params):

        if template is None:
            template = templates.BriefConcept if brief else self.template

        if brief:
            categories = {}
        else:
            categories = self._get_categories(request, objects)

        posthook = functools.partial(
            concept_posthook, request=request, embed=embed, brief=brief,
            categories=categories)

        return serialize(objects, posthook=posthook, **template)

    def is_forbidden(self, request, response, *args, **kwargs):
        "Ensure non-privileged users cannot make any changes."
        if (request.method not in SAFE_METHODS and
                not can_change_concept(request.user)):
            return True

    def is_not_found(self, request, response, pk, *args, **kwargs):
        instance = self.get_object(request, pk=pk)
        if instance is None:
            return True
        request.instance = instance
        return False


class ConceptResource(ConceptBase):
    "Resource for interacting with Concept instances."
    def get(self, request, pk):
        params = self.get_params(request)
        instance = request.instance

        if (self.checks_for_orphans and params['embed'] and
                has_orphaned_field(instance)):
            return HttpResponse(
                status=codes.internal_server_error,
                content="Could not get concept because it has one or more "
                        "orphaned fields.")

        usage.log('read', instance=instance, request=request)
        return self.prepare(request, instance, embed=params['embed'])


class ConceptFieldsResource(ConceptBase):
    "Resource for interacting with fields specific to a Concept instance."
    def prepare(self, request, instance, template=None, **params):
        if template is None:
            template = templates.ConceptField

        fields = []
        resource = FieldResource()

        if self.checks_for_orphans and has_orphaned_field(instance):
            return HttpResponse(
                status=codes.internal_server_error,
                content="Could not get concept fields because one or more are "
                        "linked to orphaned fields.")

        for cf in instance.concept_fields.select_related('field').iterator():
            field = resource.prepare(request, cf.field)
            # Add the alternate name specific to the relationship between the
            # concept and the field.
            field.update(serialize(cf, **template))
            fields.append(field)

        return fields

    def get(self, request, pk):
        instance = request.instance
        usage.log('fields', instance=instance, request=request)
        return self.prepare(request, instance)


class ConceptsResource(ConceptBase):
    def is_not_found(self, request, response, *args, **kwargs):
        return False

    def get(self, request, pk=None):
        params = self.get_params(request)

        queryset = self.get_queryset(request)

        # For privileged users, check if any filters are applied, otherwise
        # only allow for published objects.
        if can_change_concept(request.user):
            filters = {}

            if params['published'] is not None:
                filters['published'] = params['published']

            if filters:
                queryset = queryset.filter(**filters)
        else:
            queryset = queryset.published()

        # If Haystack is installed, perform the search
        if params['query'] and OPTIONAL_DEPS['haystack']:
            usage.log('search', model=self.model, request=request, data={
                'query': params['query'],
            })
            results = self.model.objects.search(
                params['query'], queryset=queryset,
                max_results=params['limit'], partial=True)
            objects = (x.object for x in results)
        else:
            if params['sort'] == 'name':
                order = '-name' if params['order'] == 'desc' else 'name'
                queryset = queryset.order_by(order)

            if params['limit']:
                queryset = queryset[:params['limit']]

            objects = queryset

        if self.checks_for_orphans and params['embed']:
            pks = []
            for obj in objects:
                if not has_orphaned_field(obj):
                    pks.append(obj.pk)
            objects = self.model.objects.filter(pk__in=pks)

        return self.prepare(request, objects, **params)


concept_resource = ConceptResource()
concept_fields_resource = ConceptFieldsResource()
concepts_resource = ConceptsResource()

# Resource endpoints
urlpatterns = patterns(
    '',
    url(r'^$', concepts_resource, name='concepts'),
    url(r'^(?P<pk>\d+)/$', concept_resource, name='concept'),
    url(r'^(?P<pk>\d+)/fields/$',
        concept_fields_resource, name='concept-fields'),
)
