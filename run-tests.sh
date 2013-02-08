#!/bin/sh

ARGS="$@"

if [ ! $ARGS ]; then
    ARGS="serrano resources tokens forms"
fi

DJANGO_SETTINGS_MODULE='tests.settings' PYTHONPATH=. coverage run `which django-admin.py` test $ARGS
rm -rf docs/coverage
coverage html
