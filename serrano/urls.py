from django.conf.urls import patterns, url, include


urlpatterns = patterns('',
    url(r'', include(patterns('',
        url(r'^$', include('serrano.resources')),
        url(r'^fields/', include('serrano.resources.datafield')),
        url(r'^concepts/', include('serrano.resources.dataconcept')),
        url(r'^contexts/', include('serrano.resources.datacontext', namespace='contexts')),
        url(r'^views/', include('serrano.resources.dataview', namespace='views')),

        url(r'^data/', include(patterns('',
            url(r'^export/', include('serrano.resources.exporter')),
            url(r'^preview/', include('serrano.resources.preview')),
        ), namespace='data')),

    ), namespace='serrano')),
)
