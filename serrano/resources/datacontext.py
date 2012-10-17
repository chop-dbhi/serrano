from django.http import HttpResponse
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from django.views.decorators.cache import never_cache
from restlib2 import resources
from restlib2.http import codes
from preserialize.serialize import serialize
from avocado.models import DataContext
from serrano.forms import DataContextForm
from . import templates


class DataContextBase(resources.Resource):
    cache_max_age = 0
    private_cache = True

    template = templates.DataContext

    @classmethod
    def prepare(self, instance):
        obj = serialize(instance, **self.template)

        # If this context is explicitly tied to a model (via the `count`)
        # specify the object names.
        if instance.model:
            opts = instance.model._meta
            obj['object_name'] = opts.verbose_name.format()
            obj['object_name_plural'] = opts.verbose_name_plural.format()

        obj['_links'] = {
            'self': {
                'rel': 'self',
                'href': reverse('serrano:datacontext', args=[instance.pk]),
            }
        }
        return obj

    @classmethod
    def get_queryset(self, request, **kwargs):
        kwargs = {}
        if hasattr(request, 'user') and request.user.is_authenticated():
            kwargs['user'] = request.user
        elif request.session.session_key:
            kwargs['session_key'] = request.session.session_key
        if kwargs:
            kwargs.setdefault('archived', False)
            return DataContext.objects.filter(**kwargs)
        return DataContext.objects.none()

    @classmethod
    def get_object(self, request, **kwargs):
        # Always assume the user for the lookup if one is present, otherwise
        # fallback to a session key
        if hasattr(request, 'user') and request.user.is_authenticated():
            kwargs['user'] = request.user
        else:
            kwargs['session_key'] = request.session.session_key

        try:
            return self.get_queryset(request).get(**kwargs)
        except DataContext.DoesNotExist:
            pass

    def is_not_found(self, request, response, **kwargs):
        if 'session' in kwargs or 'pk' in kwargs:
            instance = self.get_object(request, **kwargs)
            if instance is None:
                return True
            request.instance = instance
        return False

    def is_gone(self, request, response, **kwargs):
        if hasattr(request, 'instance'):
            return request.instance.archived


class DataContextResource(DataContextBase):
    "DataContext Summary Resource"

    def get(self, request, **kwargs):
        if 'session' in kwargs or 'pk' in kwargs:
            return self.prepare(request.instance)
        return map(self.prepare, self.get_queryset(request))

    def post(self, request):
        form = DataContextForm(request, request.data)

        if form.is_valid():
            instance = form.save(commit=False)
            form.save()
            response = HttpResponse(status=codes.created)
            self.write(request, response, self.prepare(instance))
        else:
            response = HttpResponse(status=codes.unprocessable_entity)
            self.write(request, response, dict(form.errors))
        return response

    def put(self, request, **kwargs):
        instance = request.instance
        form = DataContextForm(request, request.data, instance=instance)

        if form.is_valid():
            instance = form.save(commit=False)
            if form.count_needs_update:
                instance.count = instance.apply().distinct().count()
            form.save()
            response = HttpResponse(status=codes.ok)
            self.write(request, response, self.prepare(instance))
        else:
            response = HttpResponse(status=codes.unprocessable_entity)
            self.write(request, response, dict(form.errors))
        return response

    def delete(self, request, pk):
        if request.instance.session:
            return HttpResponse(status=codes.bad_request)
        request.instance.delete()
        return HttpResponse(status=codes.no_content)


class DataContextHistoryResource(DataContextBase):
    "DataContext History Resource"

    def get(self, request):
        queryset = self.get_queryset(request, archived=True).iterator()
        return map(self.prepare, queryset)


datacontext_resource = never_cache(DataContextResource())
datacontext_history_resource = never_cache(DataContextHistoryResource())

# Resource endpoints
urlpatterns = patterns('',
    url(r'^$', datacontext_resource, name='datacontexts'),
    url(r'^session/$', datacontext_resource, {'session': True}, name='datacontext'),
    url(r'^(?P<pk>\d+)/$', datacontext_resource, name='datacontext'),
    url(r'^history/$', datacontext_history_resource, name='datacontext-history'),
)
