from django.conf.urls import patterns, url, include
from django.views.decorators.cache import never_cache
from avocado.models import DataView
from serrano.resources import templates
from serrano.resources.base import RevisionsResource
from .templates import BriefRevisionTemplate


class NoObjectModelRevisionResource(RevisionsResource):
    """
    Resource used to test what happens to RevisionResource when no object_model
    is specified.
    """

    object_model = None
    object_model_template = templates.View
    object_model_base_uri = 'serrano:views:single'


class CustomTemplateRevisionResource(RevisionsResource):
    """
    Resource that defines a custom template and passes that to the prepare
    method instead of using the default template within the RevisionResource.
    """
    object_model = DataView
    object_model_template = templates.View
    object_model_base_uri = 'serrano:views'

    def get(self, request):
        queryset = self.get_queryset(request)
        return self.prepare(request, queryset, template=BriefRevisionTemplate)


no_object_model_resource = never_cache(NoObjectModelRevisionResource())
template_resource = never_cache(CustomTemplateRevisionResource())

urlpatterns = patterns('',
    url(r'^no_model/$', no_object_model_resource, name='no_model'),
    url(r'^template/$', template_resource, name='template'),
)
