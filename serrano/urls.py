from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^api/', include('serrano.api.urls', namespace='api')),
)
