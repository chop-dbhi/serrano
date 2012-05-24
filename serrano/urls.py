from django.conf.urls.defaults import patterns, url, include

urlpatterns = patterns('',
    url(r'^fields/', include('serrano.resources.datafield')),
    url(r'^concepts/', include('serrano.resources.dataconcept')),
)
