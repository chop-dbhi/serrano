from django.http import HttpResponse
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from django.views.decorators.cache import never_cache
from restlib2 import resources
from restlib2.http import codes
from preserialize.serialize import serialize
from avocado.models import DataView
from serrano.forms import DataViewForm
from . import templates


class DataViewBase(resources.Resource):
    cache_max_age = 0
    private_cache = True

    template = templates.DataView

    @classmethod
    def prepare(self, instance):
        obj = serialize(instance, **self.template)
        obj['_links'] = {
            'self': {
                'rel': 'self',
                'href': reverse('serrano:dataview', args=[instance.pk]),
            }
        }
        return obj

    @classmethod
    def get_queryset(self, request, **kwargs):
        if hasattr(request, 'user') and request.user.is_authenticated():
            kwargs['user'] = request.user
        elif request.session.session_key:
            kwargs['session_key'] = request.session.session_key
        if kwargs:
            kwargs.setdefault('archived', False)
            return DataView.objects.filter(**kwargs)
        return DataView.objects.none()

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
        except DataView.DoesNotExist:
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


class DataViewResource(DataViewBase):
    "DataView Summary Resource"

    def get(self, request, **kwargs):
        if 'session' in kwargs or 'pk' in kwargs:
            return self.prepare(request.instance)
        return map(self.prepare, self.get_queryset(request))

    def post(self, request):
        form = DataViewForm(request, request.data)

        if form.is_valid():
            instance = form.save()
            response = HttpResponse(status=codes.created)
            self.write(request, response, self.prepare(instance))
        else:
            response = HttpResponse(status=codes.unprocessable_entity)
            self.write(request, response, dict(form.errors))
        return response

    def put(self, request, **kwargs):
        instance = request.instance
        form = DataViewForm(request, request.data, instance=instance)

        if form.is_valid():
            instance = form.save()
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


class DataViewHistoryResource(DataViewBase):
    "DataView History Resource"

    def get(self, request):
        queryset = self.get_queryset(request, archived=True).iterator()
        return map(self.prepare, queryset)


dataview_resource = never_cache(DataViewResource())
dataview_history_resource = never_cache(DataViewHistoryResource())

# Resource endpoints
urlpatterns = patterns('',
    url(r'^$', dataview_resource, name='dataviews'),
    url(r'^session/$', dataview_resource, {'session': True}, name='dataview'),
    url(r'^(?P<pk>\d+)/$', dataview_resource, name='dataview'),
    url(r'^history/$', dataview_history_resource, name='dataview-history'),
)
