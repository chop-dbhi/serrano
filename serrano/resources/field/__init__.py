from django.conf.urls import patterns, url
from .base import FieldResource, FieldsResource
from .values import FieldValues
from .stats import FieldStats
from .dist import FieldDistribution
from .dims import FieldDimensions

field_resource = FieldResource()
fields_resource = FieldsResource()
field_values_resource = FieldValues()
field_stats_resource = FieldStats()
field_dist_resource = FieldDistribution()
field_dims_resource = FieldDimensions()

# Resource endpoints
urlpatterns = patterns(
    '',
    url(r'^$', fields_resource, name='fields'),
    url(r'^(?P<pk>\d+)/$', field_resource, name='field'),
    url(r'^(?P<pk>\d+)/values/$', field_values_resource, name='field-values'),
    url(r'^(?P<pk>\d+)/stats/$', field_stats_resource, name='field-stats'),
    url(r'^(?P<pk>\d+)/dist/$', field_dist_resource,
        name='field-distribution'),
    url(r'^(?P<pk>\d+)/dims/$', field_dims_resource,
        name='field-dimensions'),
)
