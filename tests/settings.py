import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.path.dirname(__file__), 'tests.db'),
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
    'tests.cases.resources',
    'tests.cases.forms',
    'tests.cases.tokens',
)

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

SITE_ID = 1

ROOT_URLCONF = 'tests.urls'

ANONYMOUS_USER_ID = -1

TEST_RUNNER = 'tests.runner.ProfilingTestRunner'
TEST_PROFILE = 'unittest.profile'
