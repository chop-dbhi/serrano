from django.conf.urls import url, patterns, include


urlpatterns = patterns(
    '',
    url(r'^api/', include('serrano.urls')),
    url(r'^api/test/', include('tests.resources')),
    url(r'^results/(?P<pk>\d+)/$', 'django.views.static.serve',
        {'document_root': '/results'}, name='results'),
)
