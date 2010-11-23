from django.conf.urls.defaults import *
from django.views.decorators.cache import never_cache, cache_page
from piston.resource import Resource

from serrano.api.handlers import (ScopeHandler, PerspectiveHandler, ReportHandler,
    ReportResolverHandler)

scope =  never_cache(Resource(ScopeHandler))
perspective = never_cache(Resource(PerspectiveHandler))
report = never_cache(Resource(ReportHandler))
report_resolver = never_cache(Resource(ReportResolverHandler))

category_patterns = patterns('',
    url(r'^$', 'serrano.api.resources.CategoryResource', name='read'),
)

criterion_patterns = patterns('',
    url(r'^$', 'serrano.api.resources.CriterionResource', name='read'),
    url(r'^(?P<pk>\d+)/$', 'serrano.api.resources.CriterionResource', name='read'),
)

column_patterns = patterns('',
    url(r'^$', 'serrano.api.resources.ColumnResource', name='read'),
)

# represents all of the `report` url patterns including
report_patterns = patterns('',
    url(r'^$', report, name='read'),

    # patterns relative to a particular saved instance
    url(r'^(?P<id>\d+)/', include(patterns('',
        url(r'^$', report, name='data'),
        url(r'^resolve/$', report_resolver, name='resolve'),
    ), namespace='stored')),

    # patterns relative to a temporary instance on the session
    url(r'^session/', include(patterns('',
        url(r'^$', report, {'id': 'session'}, name='data'),
        url(r'^resolve/$', report_resolver, {'id': 'session'}, name='resolve'),
    ), namespace='session'))
)

scope_patterns = patterns('',
    url(r'^$', scope, name='read'),
    url(r'^(?P<id>\d+)/$', scope, name='read'),
    url(r'^session/$', scope, {'id': 'session'}, name='session'),
)

perspective_patterns = patterns('',
    url(r'^$', perspective, name='read'),
    url(r'^(?P<id>\d+)/$', perspective, name='read'),
    url(r'^session/$', perspective, {'id': 'session'}, name='session'),
)

urlpatterns = patterns('',
    url(r'^criteria/', include(criterion_patterns, namespace='criteria')),
    url(r'^columns/', include(column_patterns, namespace='columns')),
    url(r'^categories/', include(category_patterns, namespace='categories')),
    url(r'^reports/', include(report_patterns, namespace='reports')),
    url(r'^scope/', include(scope_patterns, namespace='scope')),
    url(r'^perspectives/', include(perspective_patterns, namespace='perspectives')),
)
