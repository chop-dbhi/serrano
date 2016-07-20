from django.conf.urls import patterns, url
from django.views.decorators.cache import never_cache

from avocado.models import DataQuery
from serrano.resources import templates
from serrano.resources.history import ObjectRevisionResource, \
    ObjectRevisionsResource, RevisionsResource
from serrano.resources.query.base import PublicQueriesResource, \
    QueryResource, QueriesResource, QuerySqlResource
from serrano.resources.query.forks import QueryForksResource
from serrano.resources.query.results import QueryResultsResource
from serrano.resources.query.stats import QueryStatsResource

single_resource = never_cache(QueryResource())
active_resource = never_cache(QueriesResource())
sql_resource = never_cache(QuerySqlResource())
public_resource = never_cache(PublicQueriesResource())
forks_resource = never_cache(QueryForksResource())
stats_resource = never_cache(QueryStatsResource())
results_resource = never_cache(QueryResultsResource())

revisions_resource = never_cache(RevisionsResource(
    object_model=DataQuery, object_model_template=templates.Query,
    object_model_base_uri='serrano:queries'))
revisions_for_object_resource = never_cache(ObjectRevisionsResource(
    object_model=DataQuery, object_model_template=templates.Query,
    object_model_base_uri='serrano:queries'))
revision_for_object_resource = never_cache(ObjectRevisionResource(
    object_model=DataQuery, object_model_template=templates.Query,
    object_model_base_uri='serrano:queries'))


# Resource endpoints
urlpatterns = patterns(
    '',

    url(
        r'^$',
        active_resource,
        name='active'
    ),

    # Endpoints for specific queries
    url(
        r'^public/$',
        public_resource,
        name='public'
    ),

    # Single queries
    url(
        r'^(?P<pk>\d+)/$',
        single_resource,
        name='single'
    ),
    url(
        r'^session/$',
        single_resource,
        {'session': True},
        name='session'
    ),

    # Endpoint for retrieving results of an existing query.
    url(
        r'^(?P<pk>\d+)/results/$',
        results_resource,
        name='results'
    ),
    url(
        r'^session/results/$',
        results_resource,
        {'session': True},
        name='results'
    ),
    url(
        r'^(?P<pk>\d+)/results/(?P<page>\d+)/$',
        results_resource,
        name='results'
    ),
    url(
        r'^session/results/(?P<page>\d+)/$',
        results_resource,
        {'session': True},
        name='results'
    ),
    url(
        r'^(?P<pk>\d+)/results/(?P<page>\d+)\.\.\.(?P<stop_page>\d+)/$',
        results_resource,
        name='results'
    ),
    url(
        r'^session/results/(?P<page>\d+)\.\.\.(?P<stop_page>\d+)/$',
        results_resource,
        {'session': True},
        name='results'
    ),

    # Stats
    url(
        r'^(?P<pk>\d+)/stats/$',
        stats_resource,
        name='stats'
    ),
    url(
        r'^session/stats/$',
        stats_resource,
        {'session': True},
        name='stats'
    ),

    # SQL
    url(
        r'^(?P<pk>\d+)/sql/$',
        sql_resource,
        name='sql'
    ),
    url(
        r'^session/sql/$',
        sql_resource,
        {'session': True},
        name='sql'
    ),

    # Forks
    url(
        r'^(?P<pk>\d+)/forks/$',
        forks_resource,
        name='forks'
    ),

    # Revision related endpoints
    url(
        r'^revisions/$',
        revisions_resource,
        name='revisions'
    ),
    url(
        r'^(?P<pk>\d+)/revisions/$',
        revisions_for_object_resource,
        name='revisions_for_object'
    ),
    url(
        r'^(?P<object_pk>\d+)/revisions/(?P<revision_pk>\d+)/$',
        revision_for_object_resource,
        name='revision_for_object'
    ),
)
