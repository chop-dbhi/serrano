import os
import getpass

DATABASE_USER = os.environ.get('TEST_DATABASE_USER', getpass.getuser())
DATABASE_NAME = os.environ.get('TEST_DATABASE_NAME', 'serrano')
DATABASE_HOST = os.environ.get('TEST_DATABASE_HOST', '127.0.0.1')
DATABASE_PORT = os.environ.get('TEST_DATABASE_PORT', '5432')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': DATABASE_NAME,
        'USER': DATABASE_USER,
        'HOST': DATABASE_HOST,
        'PORT': DATABASE_PORT,
    }
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.sites',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django_rq',
    'avocado',
    'serrano',
    'tests',
    'tests.cases.base',
    'tests.cases.resources',
    'tests.cases.forms',
    'tests.cases.sets',
)

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

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

SERRANO = {
    'RATE_LIMIT_COUNT': 20,
    'RATE_LIMIT_SECONDS': 3,
    'AUTH_RATE_LIMIT_COUNT': 40,
    'AUTH_RATE_LIMIT_SECONDS': 6,
    'OBJECT_SETS': [{
        'model': 'tests.Team',
    }],
}

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
    },
    'unrelated': {
        'model': 'tests.Unrelated',
    },
}

AVOCADO_QUEUE_NAME = 'serrano_test_queue'
AVOCADO = {
    'FORCE_SYNC_LOG': True,
    'DATA_CACHE_ENABLED': False,
    'QUERY_PROCESSORS': {
        'default': 'avocado.query.pipeline.QueryProcessor',
        'manager': 'tests.processors.ManagerQueryProcessor',
        'under_twenty_thousand': 'tests.processors.UnderTwentyThousandQueryProcessor',  # noqa
        'first_title': 'tests.processors.FirstTitleQueryProcessor',
        'first_two': 'tests.processors.FirstTwoByIdQueryProcessor',
    },
    'ASYNC_QUEUE': AVOCADO_QUEUE_NAME,
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
        'rq.worker': {
            'handlers': ['null'],
            'level': 'DEBUG',
        },
    }
}

RQ_QUEUES = {
    AVOCADO_QUEUE_NAME: {
        'HOST': 'localhost',
        'PORT': 6379,
        'DB': 0,
    },
}
