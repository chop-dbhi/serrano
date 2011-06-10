from django.utils.cache import add_never_cache_headers

class NeverCache(object):
    def process_response(self, resource, request, response, **kwargs):
        add_never_cache_headers(response)


class CSRFExemption(object):
    def process_response(self, resource, request, response, **kwargs):
        response.csrf_exempt = True

