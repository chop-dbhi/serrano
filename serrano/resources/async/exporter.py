from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from avocado.query.utils import async_get_result_rows
from serrano.resources.exporter import ExporterResource, ExporterRootResource
from serrano.resources.processors import ASYNC_EXPORTER_RESULT_PROCESSOR_NAME


class AsyncExporterResource(ExporterResource):
    """
    Resource for asynchronously exporting data to the selected export format.

    This method does not return the data itself. Instead, a "see-other"
    response is returned with the ID of the job that is generating the data.
    The client can use this job ID to poll the job status and retrieve the
    result when the job is complete.

    Data is formatted using the selected export type which is supplied in the
    request URL.
    """

    def get(self, request, export_type, **kwargs):
        view = self.get_view(request)
        context = self.get_context(request)
        params = self.get_params(request)

        # Configure the query options used for retrieving the results.
        query_options = {
            'export_type': export_type,
            'query_name': self._get_query_name(request, export_type),
        }
        query_options.update(**kwargs)
        query_options.update(params)

        job_data = {
            'query_name': self._get_query_name(request, export_type),
            'user_name': request.user.username,
            'session_key': request.session.session_key,
            'result_processor': ASYNC_EXPORTER_RESULT_PROCESSOR_NAME
        }

        job_id = async_get_result_rows(
            context, view, query_options, job_data, request=request)

        return HttpResponseRedirect(
            reverse('serrano:jobs:single', kwargs={'job_uuid': job_id}))


exporter_resource = AsyncExporterResource()
exporter_root_resource = ExporterRootResource()

# Resource endpoints
urlpatterns = patterns(
    '',
    url(r'^$', exporter_root_resource, name='exporter'),
    url(
        r'^(?P<export_type>\w+)/$',
        exporter_resource,
        name='exporter'
    ),
    url(
        r'^(?P<export_type>\w+)/(?P<page>\d+)/$',
        exporter_resource,
        name='exporter'
    ),
    url(
        r'^(?P<export_type>\w+)/(?P<page>\d+)\.\.\.(?P<stop_page>\d+)/$',
        exporter_resource,
        name='exporter'
    ),
)
