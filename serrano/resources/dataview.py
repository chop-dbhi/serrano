from django.http import HttpResponse
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from restlib2 import resources, utils
from avocado.models import DataView
from serrano.forms import DataViewForm


class DataViewBase(resources.Resource):
    template = {
        'exclude': ['user', 'session_key'],
    }

    @classmethod
    def serialize(self, instance):
        obj = utils.serialize(instance, **self.template)
        obj['url'] = reverse('dataview', args=[instance.pk])
        return obj

    @classmethod
    def get_queryset(self, request, **kwargs):
        kwargs.setdefault('archived', False)
        if hasattr(request, 'user') and request.user.is_authenticated():
            kwargs['user'] = request.user
        else:
            kwargs['session_key'] = request.session.session_key
        return DataView.objects.filter(**kwargs)

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


class DataViewResource(DataViewBase):
    "DataView Summary Resource"

    def get(self, request, **kwargs):
        if 'session' in kwargs or 'pk' in kwargs:
            return self.serialize(request.instance)
        return map(self.serialize, self.get_queryset(request))

    def post(self, request):
        form = DataViewForm(request, request.data)

        if form.is_valid():
            instance = form.save()
            resp = HttpResponse(status=201)
            resp._raw_content = self.serialize(instance)
        else:
            resp = HttpResponse(status=422)
            resp._raw_content = dict(form.errors)
        return resp

        return resp

    def put(self, request, **kwargs):
        instance = request.instance
        form = DataViewForm(request, request.data, instance=instance)

        if form.is_valid():
            instance = form.save()
            resp = HttpResponse(status=200)
            resp._raw_content = self.serialize(instance)
        else:
            resp = HttpResponse(status=422)
            resp._raw_content = dict(form.errors)
        return resp


class DataViewHistoryResource(DataViewBase):
    "DataView History Resource"

    def get(self, request):
        queryset = self.get_queryset(request, archived=True).iterator()
        return map(self.serialize, queryset)


# Resource endpoints
urlpatterns = patterns('',
    url(r'^$', DataViewResource(), name='dataview'),
    url(r'^session/$', DataViewResource(), {'session': True}, name='dataview'),
    url(r'^(?P<pk>\d+)/$', DataViewResource(), name='dataview'),
    url(r'^history/$', DataViewHistoryResource(), name='dataview-history'),
)
