from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from .tokens import token_generator
from .models import ApiToken


class TokenBackend(ModelBackend):
    def authenticate(self, token):
        try:
            # NOTE: This has the limitation of requiring the token to be
            # associated with a user since non-user/non-session access is
            # not supported in Serrano.
            token = ApiToken.objects.get_active_token(token)
            return token.user
        except ApiToken.DoesNotExist:
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
