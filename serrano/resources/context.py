import functools
from django.http import HttpResponse
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from django.views.decorators.cache import never_cache
from restlib2.http import codes
from preserialize.serialize import serialize
from avocado.models import DataContext
from avocado.conf import settings
from serrano.forms import ContextForm
from .base import BaseResource
from . import templates


HISTORY_ENABLED = settings.HISTORY_ENABLED

def context_posthook(instance, data, request):
    uri = request.build_absolute_uri

    # If this context is explicitly tied to a model (via the `count`)
    # specify the object names.
    if instance.model:
        opts = instance.model._meta
        data['object_name'] = opts.verbose_name.format()
        data['object_name_plural'] = opts.verbose_name_plural.format()

    data['_links'] = {
        'self': {
            'href': uri(reverse('serrano:contexts:single', args=[instance.pk])),
        }
    }
    return data


class ContextBase(BaseResource):
    cache_max_age = 0
    private_cache = True

    template = templates.Context

    def prepare(self, request, instance, template=None):
        if template is None:
            template = self.template
        posthook = functools.partial(context_posthook, request=request)
        return serialize(instance, posthook=posthook, **template)

    def get_queryset(self, request, **kwargs):
        "Constructs a QuerySet for this user or session."

        if hasattr(request, 'user') and request.user.is_authenticated():
            kwargs['user'] = request.user
        elif request.session.session_key:
            kwargs['session_key'] = request.session.session_key
        else:
            # The only case where kwargs is empty is for non-authenticated
            # cookieless agents.. e.g. bots, most non-browser clients since
            # no session exists yet for the agent.
            return DataContext.objects.none()

        return DataContext.objects.filter(**kwargs)


class ContextsResource(ContextBase):
    "Resource of active (non-archived) contexts"
    def get(self, request):
        queryset = self.get_queryset(request, archived=False)
        return self.prepare(request, queryset)

    def post(self, request):
        form = ContextForm(request, request.data)

        if form.is_valid():
            instance = form.save(commit=False)
            form.save(archive=HISTORY_ENABLED)
            response = self.render(request, self.prepare(request, instance),
                status=codes.created)
        else:
            response = self.render(request, dict(form.errors),
                status=codes.unprocessable_entity)
        return response


class ContextsHistoryResource(ContextBase):
    "Resource of archived (non-active) contexts"
    def get(self, request):
        queryset = self.get_queryset(request, archived=True)
        return self.prepare(request, queryset)


class ContextResource(ContextBase):
    "Resource for accessing a single context"
    def get_object(self, request, pk=None, session=None, **kwargs):
        if not pk and not session:
            raise ValueError('A pk or session must used for the lookup')

        queryset = self.get_queryset(request, **kwargs)

        try:
            if pk:
                return queryset.get(pk=pk)
            else:
                return queryset.get(session=True)
        except DataContext.DoesNotExist:
            pass

    def is_not_found(self, request, response, **kwargs):
        instance = self.get_object(request, **kwargs)
        if instance is None:
            return True
        request.instance = instance

    def get(self, request, **kwargs):
        return self.prepare(request, request.instance)

    def put(self, request, **kwargs):
        instance = request.instance
        form = ContextForm(request, request.data, instance=instance)

        if form.is_valid():
            instance = form.save(commit=False)
            if form.count_needs_update:
                # Only recalculated count if conditions exist. This is to
                # prevent re-counting the entire dataset. An alternative
                # solution may be desirable such as pre-computing and
                # caching the count ahead of time.
                if instance.json:
                    instance.count = instance.apply().distinct().count()
                else:
                    instance.count = None
            form.save(archive=HISTORY_ENABLED)
            response = self.render(request, self.prepare(request, instance))
        else:
            response = self.render(request, dict(form.errors),
                status=codes.unprocessable_entity)
        return response

    def delete(self, request, **kwargs):
        if request.instance.session:
            return HttpResponse(status=codes.bad_request)
        request.instance.delete()
        return HttpResponse(status=codes.no_content)


single_resource = never_cache(ContextResource())
active_resource = never_cache(ContextsResource())
history_resource = never_cache(ContextsHistoryResource())

# Resource endpoints
urlpatterns = patterns('',
    url(r'^$', active_resource, name='active'),
    url(r'^history/$', history_resource, name='history'),

    # Endpoints for specific contexts
    url(r'^(?P<pk>\d+)/$', single_resource, name='single'),
    url(r'^session/$', single_resource, {'session': True}, name='session'),
)
