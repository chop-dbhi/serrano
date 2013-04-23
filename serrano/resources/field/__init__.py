from django.conf.urls import patterns, url
from avocado.conf import OPTIONAL_DEPS
from .base import FieldResource, FieldsResource
from .values import FieldValues
from .stats import FieldStats

field_resource = FieldResource()
fields_resource = FieldsResource()
field_values_resource = FieldValues()
field_stats_resource = FieldStats()

# Resource endpoints
urlpatterns = patterns('',
    url(r'^$', fields_resource, name='fields'),
    url(r'^(?P<pk>\d+)/$', field_resource, name='field'),
    url(r'^(?P<pk>\d+)/values/$', field_values_resource, name='field-values'),
    url(r'^(?P<pk>\d+)/stats/$', field_stats_resource, name='field-stats'),
)

if OPTIONAL_DEPS['scipy']:
    from .dist import FieldDistribution

    field_dist_resource = FieldDistribution()

    urlpatterns += patterns('',
        url(r'^(?P<pk>\d+)/dist/$', field_dist_resource, name='field-distribution'),
    )
