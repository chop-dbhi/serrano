import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'serrano.db',
    }
}

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'restlib2',
    'avocado',
    'serrano',
    'serrano.tests',
)

ROOT_URLCONF = 'serrano.urls'

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), 'templates'),
)
