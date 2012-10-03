#!/bin/sh

DJANGO_SETTINGS_MODULE='tests.settings' PYTHONPATH=. ../bin/django-admin.py shell
