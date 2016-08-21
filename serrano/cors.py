from serrano.conf import settings

# Response headers the server explicitly allows cross-origin agents to access.
# The default set based on the spec are: cache-control, content-language,
# content-type, expires, last-modified, and pragma.
exposed_headers = (
    'Content-Length',
    'Link',
    'Link-Template',
)


def is_preflight(request):
    return (request.method == 'OPTIONS' and
            'HTTP_ACCESS_CONTROL_REQUEST_METHOD' in request.META)


def patch_response(request, response, methods):
    if settings.CORS_ENABLED:
        allowed_origins = settings.CORS_ORIGINS
        origin = request.META.get('HTTP_ORIGIN')

        if not allowed_origins or origin in allowed_origins:
            # The origin must be explicitly listed when used with the
            # Access-Control-Allow-Credentials header
            # See https://developer.mozilla.org/en-US/docs/HTTP/Access_control_CORS#Access-Control-Allow-Origin # noqa
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Expose-Headers'] = ', '.join(exposed_headers)  # noqa

            if request.method == 'OPTIONS':
                response['Access-Control-Allow-Methods'] = ', '.join(methods)
                headers = request.META.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS', '')  # noqa
                if headers:
                    response['Access-Control-Allow-Headers'] = headers

    return response
