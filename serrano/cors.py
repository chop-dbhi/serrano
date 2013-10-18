from warnings import warn
from django.conf import settings


def patch_response(request, response, methods):
    if getattr(settings, 'SERRANO_CORS_ENABLED', False):
        if hasattr(settings, 'SERRANO_CORS_ORIGIN'):
            warn('SERRANO_CORS_ORIGIN has been deprecated in favor '
                 'of SERRANO_CORS_ORIGINS', DeprecationWarning)
            allowed_origins = [s.strip() for s in
                               settings.SERRANO_CORS_ORIGIN.split(',')]
        else:
            allowed_origins = getattr(settings, 'SERRANO_CORS_ORIGINS', ())

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
