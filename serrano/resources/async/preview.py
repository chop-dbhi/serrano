from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from avocado.export import HTMLExporter
from avocado.query.utils import async_get_result_rows
from serrano.resources.preview import PreviewResource
from serrano.resources.processors import ASYNC_PREVIEW_RESULT_PROCESSOR_NAME


class AsyncPreviewResource(PreviewResource):
    """
    Resource for asynchronously retrieving a data preview before exporting.

    This method does not return the data itself. Instead, a "see-other"
    response is returned with the ID of the job that is generating the data.
    The client can use this job ID to poll the job status and retrieve the
    result when the job is complete.

    Data is formatted using a JSON+HTML exporter which prefers HTML formatted
    or plain strings. Browser-based clients can consume the JSON and render
    the HTML for previewing.
    """

    def get(self, request, **kwargs):
        # Get the request's view and context
        view = self.get_view(request)
        context = self.get_context(request)

        # Configure the query options used for retrieving the results.
        query_options = {
            'export_type': HTMLExporter.short_name,
            'query_name': self._get_query_name(request),
        }
        query_options.update(**kwargs)
        query_options.update(self.get_params(request))

        job_data = {
            'query_name': self._get_query_name(request),
            'user_name': request.user.username,
            'session_key': request.session.session_key,
            'result_processor': ASYNC_PREVIEW_RESULT_PROCESSOR_NAME
        }

        job_id = async_get_result_rows(
            context, view, query_options, job_data, request=request)

        return HttpResponseRedirect(
            reverse('serrano:jobs:single', kwargs={'job_uuid': job_id}))


async_preview_resource = AsyncPreviewResource()

# Resource endpoints
urlpatterns = patterns(
    '',
    url(
        r'^$',
        async_preview_resource,
        name='preview'
    ),
    url(
        r'^(?P<page>\d+)/$',
        async_preview_resource,
        name='preview'
    ),
    url(
        r'^(?P<page>\d+)\.\.\.(?P<stop_page>\d+)/$',
        async_preview_resource,
        name='preview'
    ),
)
