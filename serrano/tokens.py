import hashlib
from datetime import datetime
from django.conf import settings
from django.utils.http import int_to_base36, base36_to_int


class TokenGenerator(object):
    def _total_seconds(self, dt):
        return int((dt - datetime(2001, 1, 1)).total_seconds())

    def _make(self, user, timestamp):
        ts_b36 = int_to_base36(timestamp)
        digest = hashlib.sha1(settings.SECRET_KEY + unicode(user.pk) + \
            user.password + unicode(timestamp)).hexdigest()[::2]
        return '{0}-{1}-{2}'.format(user.pk, ts_b36, digest)

    @property
    def timeout(self):
        return getattr(settings, 'SERRANO_TOKEN_TIMEOUT', settings.SESSION_COOKIE_AGE)

    def split(self, token):
        try:
            return token.split('-', 1)[0], token
        except ValueError:
            return None, token

    def make(self, user):
        return self._make(user, self._total_seconds(datetime.now()))

    def check(self, user, token):
        # Parse the token
        try:
            pk, ts_b36, hash = token.split('-')
        except ValueError:
            return False

        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        # Check that the timestamp/uid has not been tampered with
        if self._make(user, ts) != token:
            return False

        # Check the timestamp is within limit
        if (self._total_seconds(datetime.now()) - ts) > self.timeout:
            return False

        return True


token_generator = TokenGenerator()
