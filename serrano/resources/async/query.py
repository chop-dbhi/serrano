from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.views.decorators.cache import never_cache

from avocado.export import JSONExporter
from avocado.query.utils import async_get_result_rows
from serrano.resources.processors import ASYNC_QUERY_RESULT_PROCESSOR_NAME
from serrano.resources.query.results import QueryResultsResource


class AsyncQueryResultsResource(QueryResultsResource):
    """
    Resource for asynchronously retrieving query(session or by id) results.

    This method does not return the data itself. Instead, a "see-other"
    response is returned with the ID of the job that is generating the data.
    The client can use this job ID to poll the job status and retrieve the
    query results when the job is complete.

    Data is formatted using a JSON exporter.
    """
    def get(self, request, **kwargs):
        params = self.get_params(request)

        # Configure the query options used for retrieving the results.
        query_options = {
            'export_type': JSONExporter.short_name.lower(),
            'query_name': self._get_query_name(request),
        }
        query_options.update(**kwargs)
        query_options.update(params)

        job_data = {
            'query_name': self._get_query_name(request),
            'user_name': request.user.username,
            'session_key': request.session.session_key,
            'result_processor': ASYNC_QUERY_RESULT_PROCESSOR_NAME
        }

        job_id = async_get_result_rows(
            request.instance.context,
            request.instance.view,
            query_options,
            job_data,
            request=request)

        return HttpResponseRedirect(
            reverse('serrano:jobs:single', kwargs={'job_uuid': job_id}))


results_resource = never_cache(AsyncQueryResultsResource())

# Resource endpoints
urlpatterns = patterns(
    '',
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
)
