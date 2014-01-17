import re
import functools
from warnings import warn
from django.dispatch import receiver
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import LazyObject
from django.conf import settings as django_settings
from django.test.signals import setting_changed
from . import global_settings


SETTING_PREFIX = 'SERRANO_'
SETTING_PREFIX_LEN = len(SETTING_PREFIX)


class Settings(object):
    def __init__(self, settings_dict):
        # set the initial settings as defined in the global_settings
        for setting in dir(global_settings):
            # Ignore internal module properties
            if not setting.startswith('_'):
                setattr(self, setting, getattr(global_settings, setting))

        # iterate over the user-defined settings and override the default
        # settings
        for key, value in settings_dict.items():
            setattr(self, key, value)

    def __setattr__(self, key, value):
        if key == key.upper():
            default = getattr(self, key, None)
            if isinstance(default, dict):
                default.update(value)
            else:
                object.__setattr__(self, key, value)
        else:
            warn('Ignoring non-uppercase setting "{0}". Note that all '
                 'Serrano settings are expected to be uppercased.'.format(key))


class LazySettings(LazyObject):
    def _setup(self):
        # Assume the dict-based structure first
        user_settings = getattr(django_settings, 'SERRANO', {})

        # Build the settings dict for single settings with the prefix
        if not user_settings:
            user_settings = {}
            for setting in dir(django_settings):
                if setting.startswith(SETTING_PREFIX):
                    user_settings[setting[SETTING_PREFIX_LEN:]] = \
                        getattr(django_settings, setting)

        self._wrapped = Settings(user_settings)


settings = LazySettings()


@receiver(setting_changed)
def test_setting_changed_handler(**kwargs):
    if kwargs['setting'] == 'SERRANO':
        for key, value in kwargs['value'].items():
            setattr(settings, key, value)
    elif kwargs['setting'].startswith(SETTING_PREFIX):
        key = kwargs['setting'][SETTING_PREFIX_LEN:]
        value = kwargs['value']
        setattr(settings, key, value)


class Dependency(object):
    name = ''

    def __nonzero__(self):
        return self.installed and self.setup

    def __unicode__(self):
        return self.name

    @property
    def doc(self):
        return re.sub('\n( )+', '\n', self.__doc__ or '').strip('\n')

    @property
    def marked_doc(self):
        try:
            import markdown
        except ImportError:
            return self.doc
        return markdown.markdown(self.doc)

    def test_install(self):
        raise NotImplemented

    def test_setup(self):
        return self.test_install()

    @property
    def installed(self):
        return self.test_install() is not False

    @property
    def setup(self):
        return self.test_setup() is not False


class Objectset(Dependency):
    """django-objectset provides a set-like abstract model for Django and
    makes it trivial to creates sets of objects using common set operations.

    Install by doing `pip install django-objectset`. Define models that
    subclass `objectset.models.ObjectSet`.
    """

    name = 'objectset'

    def test_install(self):
        try:
            import objectset  # noqa
        except ImportError:
            return False


# Keep track of the officially supported apps and libraries used for various
# features.
OPTIONAL_DEPS = {
    'objectset': Objectset(),
}


def dep_supported(lib):
    return bool(OPTIONAL_DEPS[lib])


def raise_dep_error(lib):
    dep = OPTIONAL_DEPS[lib]
    raise ImproperlyConfigured(u'{0} must be installed to use '
                               'this feature.\n\n{1}'.format(lib, dep.__doc__))


def requires_dep(lib):
    "Decorator for functions that require a supported third-party library."
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            dep = OPTIONAL_DEPS[lib]
            if not dep:
                raise_dep_error(lib)
            return f(*args, **kwargs)
        return wrapper
    return decorator
