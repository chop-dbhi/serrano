from functools import wraps
from django.http import HttpResponse
from django.contrib.auth import authenticate, login
from serrano.conf import settings


def get_token(request):
    "Attempts to retrieve a token from the request."
    if 'token' in request.REQUEST:
        return request.REQUEST['token']
    if 'HTTP_API_TOKEN' in request.META:
        return request.META['HTTP_API_TOKEN']
    return ''


def check_auth(func):
    @wraps(func)
    def inner(self, request, *args, **kwargs):
        user = getattr(request, 'user', None)

        # Attempt to authenticate if a token is present
        if not user or not user.is_authenticated():
            token = get_token(request)
            user = authenticate(token=token)
            if user:
                login(request, user)
            elif settings.AUTH_REQUIRED:
                return HttpResponse(status=401)
        return func(self, request, *args, **kwargs)
    return inner
