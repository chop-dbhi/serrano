import logging
import functools
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from preserialize.serialize import serialize
from restlib2.params import Parametizer, BoolParam
from avocado.events import usage
from avocado.models import DataCategory
from .base import ThrottledResource, SAFE_METHODS
from . import templates

can_change_category = lambda u: u.has_perm('avocado.change_datacategory')
log = logging.getLogger(__name__)


def category_posthook(instance, data, request):
    """Category serialization post-hook for augmenting per-instance data.

    The only two arguments the post-hook takes is instance and data. The
    remaining arguments must be partially applied using `functools.partial`
    during the request/response cycle.
    """
    uri = request.build_absolute_uri

    data['_links'] = {
        'self': {
            'href': uri(reverse('serrano:category', args=[instance.pk])),
        },
    }

    if data['parent_id']:
        data['_links']['parent'] = {
            'href': uri(reverse('serrano:category', args=[data['parent_id']])),
        }

    return data


class CategoryParametizer(Parametizer):
    "Supported params and their defaults for Category endpoints."

    unpublished = BoolParam(False)


class CategoryBase(ThrottledResource):
    "Base resource for Category-related data."

    model = DataCategory

    template = templates.Category

    parametizer = CategoryParametizer

    def get_queryset(self, request):
        queryset = self.model.objects.all()
        if not can_change_category(request.user):
            queryset = queryset.published()
        return queryset

    def get_object(self, request, **kwargs):
        if not hasattr(request, 'instance'):
            queryset = self.get_queryset(request)

            try:
                instance = queryset.get(**kwargs)
            except self.model.DoesNotExist:
                instance = None

            request.instance = instance

        return request.instance

    def prepare(self, request, objects, template=None, **params):
        posthook = functools.partial(category_posthook, request=request)
        return serialize(objects, posthook=posthook, **self.template)

    def is_forbidden(self, request, response, *args, **kwargs):
        "Ensure non-privileged users cannot make any changes."
        if (request.method not in SAFE_METHODS and
                not can_change_category(request.user)):
            return True

    def is_not_found(self, request, response, pk, *args, **kwargs):
        return self.get_object(request, pk=pk) is None


class CategoryResource(CategoryBase):
    "Resource for interacting with Category instances."
    def get(self, request, pk):
        instance = self.get_object(request, pk=pk)

        usage.log('read', instance=instance, request=request)
        return self.prepare(request, instance)


class CategoriesResource(CategoryBase):
    def is_not_found(self, request, response, *args, **kwargs):
        return False

    def get(self, request, pk=None):
        params = self.get_params(request)

        queryset = self.get_queryset(request)

        # For privileged users, check if any filters are applied, otherwise
        # only allow for published objects.
        if not can_change_category(request.user) or not params['unpublished']:
            queryset = queryset.published()

        return self.prepare(request, queryset, **params)


category_resource = CategoryResource()
categories_resource = CategoriesResource()

# Resource endpoints
urlpatterns = patterns(
    '',
    url(r'^$', categories_resource, name='categories'),
    url(r'^(?P<pk>\d+)/$', category_resource, name='category'),
)
