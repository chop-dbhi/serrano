from django.conf.urls import url, patterns, include


urlpatterns = patterns('',
    url(r'^api/', include('serrano.urls')),
)
