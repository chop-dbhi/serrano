from django.conf.urls.defaults import *
from django.conf import settings

urlpatterns = patterns('',
    # authentication    
    url(r'^login/$', 'serrano.views.login',
        {'template_name': 'login.html'}, name='login'),
    url(r'^logout/$', 'django.contrib.auth.views.logout_then_login',
        name='logout'),

    url(r'^define/$', 'serrano.views.define', name='define'),
    url(r'^report/$', 'serrano.views.report', name='report'),

    # API
    url(r'^api/', include('serrano.api.urls', namespace='api')),
)