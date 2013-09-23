from django.conf.urls import patterns, url, include


urlpatterns = patterns(
    '',
    url(r'', include(patterns('',
        url(r'^$', include('serrano.resources')),
        url(r'^fields/', include('serrano.resources.field')),
        url(r'^concepts/', include('serrano.resources.concept')),
        url(r'^contexts/',
            include('serrano.resources.context', namespace='contexts')),
        url(r'^queries/',
            include('serrano.resources.query', namespace='queries')),
        url(r'^views/', include('serrano.resources.view', namespace='views')),

        url(r'^data/', include(patterns(
            '',
            url(r'^export/', include('serrano.resources.exporter')),
            url(r'^preview/', include('serrano.resources.preview')),
            ), namespace='data')),

        ), namespace='serrano')),
)
