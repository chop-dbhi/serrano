from django.conf.urls import patterns, url
from avocado.conf import OPTIONAL_DEPS
from .base import DataFieldResource, DataFieldsResource
from .values import DataFieldValues
from .stats import DataFieldStats

datafield_resource = DataFieldResource()
datafields_resource = DataFieldsResource()
datafield_values_resource = DataFieldValues()
datafield_stats_resource = DataFieldStats()

# Resource endpoints
urlpatterns = patterns('',
    url(r'^$', datafields_resource, name='datafields'),
    url(r'^(?P<pk>\d+)/$', datafield_resource, name='datafield'),
    url(r'^(?P<pk>\d+)/values/$', datafield_values_resource, name='datafield-values'),
    url(r'^(?P<pk>\d+)/stats/$', datafield_stats_resource, name='datafield-stats'),
)

if OPTIONAL_DEPS['scipy']:
    from .dist import DataFieldDistribution

    datafield_dist_resource = DataFieldDistribution()

    urlpatterns += patterns('',
        url(r'^(?P<pk>\d+)/dist/$', datafield_dist_resource, name='datafield-distribution'),
    )
