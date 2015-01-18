import logging
import functools
from django.db.models import Q
from django.conf.urls import patterns, url
from preserialize.serialize import serialize
from restlib2.http import codes
from restlib2.params import Parametizer, BoolParam, StrParam, IntParam
from modeltree.tree import MODELTREE_DEFAULT_ALIAS, trees
from avocado.events import usage
from avocado.models import DataField, DataConcept, DataCategory
from avocado.conf import OPTIONAL_DEPS
from .base import ThrottledResource, SAFE_METHODS
from . import templates
from .field import base as FieldResources
from ..links import reverse_tmpl


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


def concept_posthook(instance, data, request, categories=None):
    """Concept serialization post-hook for augmenting per-instance data.

    The only two arguments the post-hook takes is instance and data. The
    remaining arguments must be partially applied using `functools.partial`
    during the request/response cycle.
    """
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

    fields = []
    for cf in instance.concept_fields.select_related('field').iterator():
        fields.append({
            'description': cf.field.description,
            'name': cf.field.name,
            'pk': cf.field.pk,
            'alt_name': cf.__unicode__(),
            'alt_plural_name': cf.get_plural_name(),
        })

    data['fields'] = fields

    return data


class ConceptParametizer(Parametizer):
    "Supported params and their defaults for Concept endpoints."

    tree = StrParam(MODELTREE_DEFAULT_ALIAS, choices=trees)
    sort = StrParam()
    order = StrParam('asc')
    unpublished = BoolParam(False)
    brief = BoolParam(False)
    query = StrParam()
    limit = IntParam()


class ConceptBase(ThrottledResource):
    "Base resource for Concept-related data."

    model = DataConcept

    template = templates.Concept

    parametizer = ConceptParametizer

    def get_link_templates(self, request):
        uri = request.build_absolute_uri

        params = self.get_params(request)

        templates = {}

        if not params['brief']:
            templates['self'] = reverse_tmpl(
                uri, 'serrano:concept', {'pk': (int, 'id')})

        return templates

    def get_queryset(self, request, params):
        # Filter by the selected tree.
        tree = trees[params['tree']]

        q = Q()

        # No public method for accessing the local models on the tree
        # Exclude concepts that contain any unrelated fields.
        for app_name, model_name in tree._models:
            q &= ~Q(app_name=app_name, model_name=model_name)

        unrelated_fields = DataField.objects.filter(q)

        queryset = self.model.objects.exclude(fields__in=unrelated_fields)

        if params.get('unpublished') and can_change_concept(request.user):
            return queryset

        return queryset.published(user=request.user)

    def get_object(self, request, **kwargs):
        if not hasattr(request, 'instance'):
            queryset = self.get_queryset(request, self.get_params(request))

            try:
                instance = queryset.get(**kwargs)
            except self.model.DoesNotExist:
                instance = None

            request.instance = instance

        return request.instance

    def _get_categories(self, request, objects):
        """Returns a QuerySet of categories for use during serialization.

        Since `category` is a nullable relationship to `concept`, a lookup
        would have to occur for every concept being serialized. This returns
        a QuerySet applicable to the resource using it and is cached for the
        remainder of the request/response cycle.
        """
        return dict((x.pk, x) for x in list(DataCategory.objects.all()))

    def prepare(self, request, objects, template=None, brief=False, **params):

        if template is None:
            template = templates.BriefConcept if brief else self.template

        if brief:
            categories = {}
        else:
            categories = self._get_categories(request, objects)

        posthook = functools.partial(
            concept_posthook, request=request, categories=categories)

        return serialize(objects, posthook=posthook, **template)

    def is_forbidden(self, request, response, *args, **kwargs):
        "Ensure non-privileged users cannot make any changes."
        if (request.method not in SAFE_METHODS and
                not can_change_concept(request.user)):
            return True

    def is_not_found(self, request, response, pk, *args, **kwargs):
        return self.get_object(request, pk=pk) is None


class ConceptResource(ConceptBase):
    "Resource for interacting with Concept instances."
    def get(self, request, pk):
        instance = self.get_object(request, pk=pk)

        if (self.checks_for_orphans and has_orphaned_field(instance)):
            data = {
                'message': 'One or more orphaned fields exist'
            }
            return self.render(request, data,
                               status=codes.internal_server_error)

        usage.log('read', instance=instance, request=request)
        return self.prepare(request, instance)


class ConceptsResource(ConceptBase):
    def is_not_found(self, request, response, *args, **kwargs):
        return False

    def _get_non_orphans(self, queryset):
        pks = []

        for obj in queryset:
            if not has_orphaned_field(obj):
                pks.append(obj.pk)

        return queryset.filter(pk__in=pks)

    def get(self, request, pk=None):
        params = self.get_params(request)

        order = ['-category__order' if params['order'] == 'desc'
                 else 'category__order']

        queryset = self.get_queryset(request, params)

        if params['query']:
            usage.log('search', model=self.model, request=request, data={
                'query': params['query'],
            })

            if self.checks_for_orphans:
                queryset = self._get_non_orphans(queryset)

            queryset = self.model.objects.search(
                params['query'], queryset=queryset,
                max_results=params['limit'], partial=True)

            # If we searched using haystack then we need to extract the objects
            # from the returned queryset. Otherwise, we can just use the
            # queryset directly.
            if OPTIONAL_DEPS['haystack']:
                objects = (x.object for x in queryset)
            else:
                objects = queryset
        else:
            if params['sort'] == 'name':
                order.append('-name' if params['order'] == 'desc'
                             else 'name')

            # We need to order before a possible slice is taken because
            # querysets cannot be ordered post-slice.
            queryset = queryset.order_by(*order)

            if self.checks_for_orphans:
                queryset = self._get_non_orphans(queryset)

            if params['limit']:
                queryset = queryset[:params['limit']]

            objects = queryset

        return self.prepare(request, objects, **params)


concept_resource = ConceptResource()
concepts_resource = ConceptsResource()

# Resource endpoints
urlpatterns = patterns(
    '',
    url(r'^$', concepts_resource, name='concepts'),
    url(r'^(?P<pk>\d+)/$', concept_resource, name='concept'),
)
