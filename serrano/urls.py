from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^api/', include('serrano.api.urls', namespace='api')),
    url(r'^reports/(?P<pk>\d+)/$', 'serrano.api.resources.ReportRedirectResource',
        name='report-redirect'),
)
