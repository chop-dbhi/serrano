from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.conf import settings
from .tokens import token_generator
from .models import ApiToken


class TokenBackend(ModelBackend):
    def authenticate(self, token):
        # For backwards compatibility only use the ApiToken model if
        # Serrano is installed as an app as this was not a requirement
        # previously.
        if 'serrano' in settings.INSTALLED_APPS:
            # NOTE: This has the limitation of requiring the token to be
            # associated with a user since non-user/non-session access is
            # not supported in Serrano.
            try:
                token = ApiToken.objects.get_active_token(token)
                return token.user
            except ApiToken.DoesNotExist:
                pass

        pk, token = token_generator.split(token)

        try:
            pk = int(pk)
        except (ValueError, TypeError):
            return

        try:
            user = User.objects.get(pk=pk, is_active=True)
        except User.DoesNotExist:
            return

        if token_generator.check(user, token):
            return user
