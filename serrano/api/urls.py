from django.conf.urls.defaults import *

category_patterns = patterns('serrano.api.resources',
    url(r'^$', 'CategoryResourceCollection', name='read'),
    url(r'^(?P<pk>\d+)/$', 'CategoryResource', name='read'),
)

criterion_patterns = patterns('serrano.api.resources',
    url(r'^$', 'CriterionResourceCollection', name='read'),
    url(r'^(?P<pk>\d+)/$', 'CriterionResource', name='read'),
)

column_patterns = patterns('serrano.api.resources',
    url(r'^$', 'ColumnResourceCollection', name='read'),
)

report_patterns = patterns('serrano.api.resources',
    url(r'^$', 'ReportResourceCollection', name='read'),
    url(r'^(?P<pk>\d+)/$', 'ReportResource', name='read'),
    url(r'^session/$', 'SessionReportResource', name='session'),
)

scope_patterns = patterns('serrano.api.resources',
    url(r'^$', 'ScopeResourceCollection', name='read'),
    url(r'^(?P<pk>\d+)/$', 'ScopeResource', name='read'),
    url(r'^session/$', 'SessionScopeResource', name='session'),
)

perspective_patterns = patterns('serrano.api.resources',
    url(r'^$', 'PerspectiveResourceCollection', name='read'),
    url(r'^(?P<pk>\d+)/$', 'PerspectiveResource', name='read'),
    url(r'^session/$', 'SessionPerspectiveResource', name='session'),
)

urlpatterns = patterns('',
    url(r'^criteria/', include(criterion_patterns, namespace='criteria')),
    url(r'^columns/', include(column_patterns, namespace='columns')),
    url(r'^domains/', include(category_patterns, namespace='categories')),
    url(r'^reports/', include(report_patterns, namespace='reports')),
    url(r'^scope/', include(scope_patterns, namespace='scope')),
    url(r'^perspectives/', include(perspective_patterns, namespace='perspectives')),
)
