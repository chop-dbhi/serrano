import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.path.dirname(__file__), 'tests.db'),
        'TEST_NAME': os.path.join(os.path.dirname(__file__), 'tests.db'),
    }
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.sites',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'avocado',
    'serrano',
    'tests',
    'tests.cases.base',
    'tests.cases.resources',
    'tests.cases.forms',
)

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 1025

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'serrano.middleware.SessionMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'serrano.backends.TokenBackend',
)

SERRANO_RATE_LIMIT_COUNT=20
SERRANO_AUTH_RATE_LIMIT_COUNT=40
SERRANO_RATE_LIMIT_SECONDS=3
SERRANO_AUTH_RATE_LIMIT_SECONDS=6

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

SITE_ID = 1

ROOT_URLCONF = 'tests.urls'

ANONYMOUS_USER_ID = -1

TEST_RUNNER = 'tests.runner.ProfilingTestRunner'
TEST_PROFILE = 'unittest.profile'

SECRET_KEY = 'abc123'

MODELTREES = {
    'default': {
        'model': 'tests.Employee',
    }
}

AVOCADO = {
    'FORCE_SYNC_LOG': True,
}

# Switch handlers from 'null' => 'console' to see logging output
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler'
        }
    },
    'loggers': {
        'avocado': {
            'handlers': ['null'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'serrano': {
            'handlers': ['null'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}
