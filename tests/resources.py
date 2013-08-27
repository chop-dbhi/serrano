from django.conf.urls import patterns, url, include
from django.views.decorators.cache import never_cache
from avocado.models import DataView
from serrano.resources import templates
from serrano.resources.base import HistoryResource

class NoObjectModelHistoryResource(HistoryResource):
    """
    Resource used to test what happens to HistoryResource when no object_model
    is specified.
    """

    object_model = None
    object_model_template = templates.View
    object_model_uri = 'serrano:views:single'


no_object_model_resource = never_cache(NoObjectModelHistoryResource())

urlpatterns = patterns('',
    url(r'^no_model/$', no_object_model_resource, name='no_model'),
)
