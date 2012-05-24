#!/bin/sh

DJANGO_SETTINGS_MODULE='serrano.tests.settings' PYTHONPATH=. coverage run ../bin/django-admin.py test serrano
rm -rf docs/coverage
coverage html
