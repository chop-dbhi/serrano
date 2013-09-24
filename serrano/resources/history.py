import functools
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from preserialize.serialize import serialize
from restlib2.params import Parametizer, BoolParam
from avocado.history.models import Revision
from .base import ThrottledResource
from . import templates

__all__ = ('RevisionParametizer', 'RevisionsResource',
           'ObjectRevisionResource', 'ObjectRevisionsResource')


def revision_posthook(instance, data, request, object_uri, object_template,
                      embed=False):
    uri = request.build_absolute_uri

    data['_links'] = {
        'self': {
            'href': uri(reverse("{0}:revision_for_object".format(object_uri),
                                args=[instance.object_id, instance.pk])),
        },
        'object': {
            'href': uri(reverse("{0}:single".format(object_uri),
                                args=[instance.object_id])),
        }
    }

    if embed:
        data['object'] = serialize(instance.content_object, **object_template)

    return data


class RevisionParametizer(Parametizer):
    """
    Support params and their defaults for Revision endpoints.
    """
    embed = BoolParam(False)


class RevisionsResource(ThrottledResource):
    cache_max_age = 0
    private_cache = True

    object_model = None
    object_model_template = None
    object_model_base_uri = None

    model = Revision
    template = templates.Revision

    parametizer = RevisionParametizer

    def prepare(self, request, instance, template=None, embed=False):
        if template is None:
            template = self.template
        posthook = functools.partial(
            revision_posthook, request=request,
            object_uri=self.object_model_base_uri,
            object_template=self.object_model_template, embed=embed)
        return serialize(instance, posthook=posthook, **template)

    def get_queryset(self, request, **kwargs):
        "Constructs a QuerySet for this user or session from past revisions."
        if not self.object_model:
            return self.model.objects.none()

        if hasattr(request, 'user') and request.user.is_authenticated():
            kwargs['user'] = request.user
        elif request.session.session_key:
            kwargs['session_key'] = request.session.session_key
        else:
            # The only case where kwargs is empty is for non-authenticated
            # cookieless agents.. e.g. bots, most non-browser clients since
            # no session exists yet for the agent.
            return self.model.objects.none()

        kwargs['content_type'] = ContentType.objects.get_for_model(
            self.object_model)

        return self.model.objects.filter(**kwargs)

    def get(self, request):
        params = self.get_params(request)
        queryset = self.get_queryset(request)

        return self.prepare(request, queryset, embed=params['embed'])


class ObjectRevisionsResource(RevisionsResource):
    """
    Resource for retrieving all revisions of an object model.
    """
    def get(self, request, **kwargs):
        query_kwargs = {'object_id': int(kwargs['pk'])}

        params = self.get_params(request)
        queryset = self.get_queryset(request, **query_kwargs)

        return self.prepare(request, queryset, embed=params['embed'])


class ObjectRevisionResource(RevisionsResource):
    """
    Resource for retrieving a single revision related to a single object model.
    """
    def get_object(self, request, object_pk=None, revision_pk=None, **kwargs):
        if not object_pk:
            raise ValueError("An object model id must be supplied for "
                             "the lookup")
        if not revision_pk:
            raise ValueError('A Revision id must be supplied for the lookup')

        queryset = self.get_queryset(request, **kwargs)

        try:
            return queryset.get(pk=revision_pk, object_id=object_pk)
        except self.model.DoesNotExist:
            pass

    def is_not_found(self, request, response, **kwargs):
        try:
            instance = self.get_object(request, **kwargs)
        except ValueError:
            return True

        if instance is None:
            return True
        request.instance = instance

    def get(self, request, **kwargs):
        return self.prepare(request, request.instance)
