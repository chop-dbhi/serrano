from django.conf.urls.defaults import *

category_patterns = patterns('serrano.api.resources',
    url(r'^$', 'CategoryResourceCollection', name='read'),
)

criterion_patterns = patterns('serrano.api.resources',
    url(r'^$', 'CriterionResourceCollection', name='read'),
    url(r'^(?P<pk>\d+)/$', 'CriterionResource', name='read'),
)

column_patterns = patterns('serrano.api.resources',
    url(r'^$', 'ColumnResourceCollection', name='read'),
)

# represents all of the `report` url patterns including
report_patterns = patterns('serrano.api.resources',
    url(r'^$', 'ReportResourceCollection', name='read'),

    # patterns relative to a particular saved instance
    url(r'^(?P<pk>\d+)/', include(patterns('serrano.api.resources',
        url(r'^$', 'ReportResource', name='data'),
        url(r'^resolve/$', 'ReportResolverResource', name='resolve'),
    ), namespace='stored')),

    # patterns relative to a temporary instance on the session
    url(r'^session/', include(patterns('serrano.api.resources',
        url(r'^$', 'ReportResource', {'pk': 'session'}, name='data'),
        url(r'^resolve/$', 'ReportResolverResource', {'pk': 'session'}, name='resolve'),
    ), namespace='session'))
)

scope_patterns = patterns('serrano.api.resources',
    url(r'^$', 'ScopeResourceCollection', name='read'),
    url(r'^(?P<pk>\d+)/$', 'ScopeResource', name='read'),
    url(r'^session/$', 'ScopeResource', {'pk': 'session'}, name='session'),
)

perspective_patterns = patterns('serrano.api.resources',
    url(r'^$', 'PerspectiveResourceCollection', name='read'),
    url(r'^(?P<pk>\d+)/$', 'PerspectiveResource', name='read'),
    url(r'^session/$', 'PerspectiveResource', {'pk': 'session'}, name='session'),
)

urlpatterns = patterns('',
    url(r'^criteria/', include(criterion_patterns, namespace='criteria')),
    url(r'^columns/', include(column_patterns, namespace='columns')),
    url(r'^categories/', include(category_patterns, namespace='categories')),
    url(r'^reports/', include(report_patterns, namespace='reports')),
    url(r'^scope/', include(scope_patterns, namespace='scope')),
    url(r'^perspectives/', include(perspective_patterns, namespace='perspectives')),
)
