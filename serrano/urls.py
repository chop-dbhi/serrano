from django.conf.urls import patterns, url, include
from serrano.conf import dep_supported


# Patterns for the data namespace
data_patterns = patterns(
    '',

    url(r'^export/', include('serrano.resources.exporter')),

    url(r'^preview/', include('serrano.resources.preview')),
)

# Patterns for the serrano namespace
serrano_patterns = patterns(
    '',

    url(r'^',
        include('serrano.resources')),

    url(r'^categories/',
        include('serrano.resources.category')),

    url(r'^fields/',
        include('serrano.resources.field')),

    url(r'^concepts/',
        include('serrano.resources.concept')),

    url(r'^contexts/',
        include('serrano.resources.context', namespace='contexts')),

    url(r'^queries/',
        include('serrano.resources.query', namespace='queries')),

    url(r'^views/',
        include('serrano.resources.view', namespace='views')),

    url(r'^data/', include(data_patterns, namespace='data')),
)

if dep_supported('objectset'):
    # Patterns for the 'sets' namespace
    serrano_patterns += patterns(
        '',
        url(r'^sets/', include('serrano.resources.sets', namespace='sets'))
    )

# Exported patterns
urlpatterns = patterns(
    '',
    url(r'^', include(serrano_patterns, namespace='serrano'))
)
