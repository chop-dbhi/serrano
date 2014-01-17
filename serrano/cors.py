from serrano.conf import settings


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
            if request.method == 'OPTIONS':
                response['Access-Control-Allow-Methods'] = ', '.join(methods)
                headers = request.META.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS')  # noqa
                if headers:
                    response['Access-Control-Allow-Headers'] = headers
    return response
