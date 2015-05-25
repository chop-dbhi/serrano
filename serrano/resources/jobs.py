from django.conf.urls import patterns, url
from django.http import Http404

from avocado.async import utils
from serrano.links import reverse_tmpl
from serrano.resources.base import ThrottledResource
from serrano.resources.processors import process_results


class JobResource(ThrottledResource):
    """
    Resource for getting information about a single job.
    """
    def is_not_found(self, request, response, **kwargs):
        return self.get_object(request, **kwargs) is None

    def get_object(self, request, **kwargs):
        """
        Lookup the job and return it or return None if the job wasn't found.
        """
        if not hasattr(request, 'instance'):
            request.instance = utils.get_job(kwargs['job_uuid'])

        return request.instance

    def get_link_templates(self, request):
        """
        Return the link templates for this job.

        These include a link to this job and a link to this job's result.
        """
        uri = request.build_absolute_uri

        return {
            'self': reverse_tmpl(
                uri, 'serrano:jobs:single', {'job_uuid': (int, 'id')}),
            'result': reverse_tmpl(
                uri, 'serrano:jobs:result', {'job_uuid': (int, 'id')}),
        }

    def get(self, request, **kwargs):
        """
        Return the ID and current status of this job.

        If a job with the supplied ID could not be found, this will return 404.
        """
        return {
            'id': request.instance.id,
            'status': request.instance.get_status(),
        }

    def delete(self, request, **kwargs):
        """
        Delete the job.

        If the job with the supplied ID is not found, this will return a 404.
        """
        return utils.cancel_job(request.instance.id)


class JobResultResource(JobResource):
    """
    Resource for getting the result of a single job.
    """
    def get_link_templates(self, request):
        """
        Returns a link to this job result.
        """
        uri = request.build_absolute_uri

        return {
            'self': reverse_tmpl(
                uri, 'serrano:jobs:result', {'job_uuid': (int, 'id')}),
        }

    def get(self, request, **kwargs):
        """
        Returns the result of the job with the supplied ID.

        If the job could not be found or the job has not completed yet, this
        will return a 404.

        Since different jobs are started from different async endpoints, there
        might be some post-job processing to do on the results and the
        intended response object.

        NOTE: Given no knowledge of the method for storing the job result,
        this method might also return a 404 if the job completed in the past
        but the result has been culled because the result expired or was
        replaced such as is the case in some in-memory storage systems. This
        method makes no assumption of that as the job management is handled
        by Avocado and this method should be independent of the async system
        used for creating and running jobs.
        """
        result = request.instance.result

        if result is None:
            raise Http404

        return process_results(
            request, request.instance.meta['result_processor'], result)


single_resource = JobResource()
result_resource = JobResultResource()


urlpatterns = patterns(
    '',
    url(
        r'^(?P<job_uuid>[-\w]+)/$',
        single_resource,
        name='single'
    ),
    url(
        r'^(?P<job_uuid>[-\w]+)/result/$',
        result_resource,
        name='result'
    ),
)
