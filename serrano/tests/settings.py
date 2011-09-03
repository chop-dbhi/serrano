MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'avocado.store.middleware.SessionReportMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'serrano.db',
    }
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.contenttypes',
    'restlib',
    'avocado',
    'serrano',
    'serrano.tests',
)

COVERAGE_MODULES = (
    'serrano.api.resources.perspective',
    'serrano.api.resources.scope',
    'serrano.api.resources.report',
)

TEST_RUNNER = 'serrano.tests.coverage_test.CoverageTestRunner'

ROOT_URLCONF = 'serrano.urls'

AVOCADO_SETTINGS = {
    'MODELTREES': {
        'default': {
            'root_model': 'avocado.Category',
        }
    },
}
