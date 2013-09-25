import hashlib
import sys
from datetime import datetime
from django.conf import settings
from django.utils.http import int_to_base36, base36_to_int


class TokenGenerator(object):
    def _total_seconds(self, dt):
        """
        Computes the number of seconds in a datetime.timedelta object.

        Ideally, this is done just using the built in total seconds method
        but if the python version we are running on is < 2.7 we manually
        compute the number of seconds in the delta and return that. The
        manual computation method comes from the Python docs here:

        http://docs.python.org/2/library/datetime.html#datetime.timedelta.total_seconds  # noqa

        NOTE: Manual computation opens us up to possible loss of precision but
        it's the best we can do in Python < 2.7.
        """
        # The number of seconds in a day
        SEC_PER_DAY = 24 * 3600
        # The number of microseconds in a second
        MICROSEC_PER_SEC = 10**6

        timedelta = (dt - datetime(2001, 1, 1))

        if sys.version_info >= (2, 7):
            return int(timedelta.total_seconds())
        else:
            # Get the microseconds from the timedelta itself.
            microseconds = timedelta.microseconds

            # Add the microseconds contribution from the seconds of the
            # timedelta.
            microseconds += timedelta.seconds * MICROSEC_PER_SEC

            # Add the microseconds contribution from the days property of the
            # timedelta.
            microseconds += timedelta.days * SEC_PER_DAY * MICROSEC_PER_SEC

            # Convert the microseconds to seconds
            return int(microseconds / MICROSEC_PER_SEC)

    def _make(self, user, timestamp):
        ts_b36 = int_to_base36(timestamp)
        total = (settings.SECRET_KEY + unicode(user.pk) + user.password +
                 unicode(timestamp))
        digest = hashlib.sha1(total).hexdigest()[::2]
        return '{0}-{1}-{2}'.format(user.pk, ts_b36, digest)

    @property
    def timeout(self):
        return getattr(settings, 'SERRANO_TOKEN_TIMEOUT',
                       settings.SESSION_COOKIE_AGE)

    def split(self, token):
        try:
            return token.split('-', 1)[0], token
        except AttributeError:
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
