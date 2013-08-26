from django.conf.urls import url, patterns, include


urlpatterns = patterns('',
    url(r'^api/', include('serrano.urls')),
    url(r'^api/test/', include('tests.resources')),
)
