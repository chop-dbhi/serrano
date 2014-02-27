from django.db import models
from django.contrib.auth.models import User
from .tokens import generate_random_token


def unique_token(token):
    return not ApiToken.objects.filter(token=token).exists()


class ApiTokenManager(models.Manager):
    def get_active_tokens(self):
        return self.get_query_set().select_related('user')\
            .filter(user__is_active=True, revoked=False)

    def get_active_token(self, token):
        return self.get_active_tokens().get(token=token)


class ApiToken(models.Model):
    "Token for use as authentication for API access."
    user = models.ForeignKey(User)
    token = models.CharField(max_length=32, editable=False)
    revoked = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    objects = ApiTokenManager()

    class Meta(object):
        verbose_name = 'API Token'

    def __unicode__(self):
        return u"{0}'s API Token".format(self.user)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = generate_random_token(32, test=unique_token)
        return super(ApiToken, self).save(*args, **kwargs)
