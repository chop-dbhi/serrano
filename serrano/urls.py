from django.conf.urls.defaults import patterns, url, include

urlpatterns = patterns('',
    url(r'^fields/', include('serrano.resources.datafield')),
    url(r'^concepts/', include('serrano.resources.dataconcept')),
    url(r'^contexts/', include('serrano.resources.datacontext')),
    url(r'^views/', include('serrano.resources.dataview')),
    url(r'^data/', include('serrano.resources.exporter')),
)
