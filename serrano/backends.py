from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from .tokens import token_generator


class TokenBackend(ModelBackend):
    def authenticate(self, token):
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
