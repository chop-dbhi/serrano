from django.conf.urls import patterns, url, include
from django.views.decorators.cache import never_cache
from avocado.models import DataView
from serrano.resources import templates
from serrano.resources.base import HistoryResource

class TestHistoryResource(HistoryResource):
    "Simple resource to test the HistoryResource base class"

    object_model = DataView
    object_model_template = templates.View

    def get(self, request):
        queryset = self.get_queryset(request)
        return self.prepare(request, queryset)


class NoObjectModelHistoryResource(HistoryResource):
    """
    Resource used to test what happens to HistoryResource when no object_model
    is specified.
    """

    object_model = None
    object_model_template = templates.View

    def get(self, request):
        queryset = self.get_queryset(request)
        return self.prepare(request, queryset)


test_resource = never_cache(TestHistoryResource())
no_object_model_resource = never_cache(NoObjectModelHistoryResource())

urlpatterns = patterns('',
    url(r'^views/$', test_resource, name='test'),
    url(r'^no_model/$', no_object_model_resource, name='no_model'),
)
