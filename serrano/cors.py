import re
from django.conf import settings

http_header = re.compile(r'^HTTP_(.+)')

def _clean_header(s):
    return s.lower().replace('_', '-')

def _request_headers(request):
    if 'HTTP_ACCESS_CONTROL_REQUEST_HEADERS' in request.META:
        return request.META['HTTP_ACCESS_CONTROL_REQUEST_HEADERS']

    headers = []
    if 'CONTENT_LENGTH' in request.META:
        headers.append(_clean_header('CONTENT_LENGTH'))
    if 'CONTENT_TYPE' in request.META:
        headers.append(_clean_header('CONTENT_TYPE'))
    for key in request.META:
        match = http_header.match(key)
        if match:
            headers.append(_clean_header(match.groups()[0]))
    return ', '.join(headers)

def patch_response(request, response, allowed_methods):
    if getattr(settings, 'SERRANO_CORS_ENABLED', False):
        response['Access-Control-Allow-Origin'] = getattr(settings, 'SERRANO_CORS_ORIGIN', '*')
        response['Access-Control-Allow-Methods'] = ', '.join(allowed_methods)
        response['Access-Control-Allow-Headers'] = _request_headers(request)
    return response
