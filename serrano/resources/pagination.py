from django.core.paginator import Paginator
from restlib2.params import Parametizer, IntParam
from restlib2.resources import Resource

__all__ = ('PaginatorResource', 'PaginatorParametizer')


class PaginatorParametizer(Parametizer):
    page = IntParam(1)
    limit = IntParam(20)


class PaginatorResource(Resource):
    parametizer = PaginatorParametizer

    def get_paginator(self, queryset, limit):
        return Paginator(queryset, per_page=limit)

    def get_page_links(self, request, path, page, extra=None):
        "Returns the page links."
        uri = request.build_absolute_uri

        # format string will be expanded below
        params = {
            'page': '{0}',
            'limit': '{1}',
        }

        if extra:
            for key, value in extra.items():
                # Use the original GET parameter if supplied and if the
                # cleaned value is valid
                if key in request.GET and value is not None and value != '':
                    params.setdefault(key, request.GET.get(key))

        # Stringify parameters. Since these are the original GET params,
        # they do not need to be encoded
        pairs = sorted(['{0}={1}'.format(k, v) for k, v in params.items()])

        # Create path string
        path_format = '{0}?{1}'.format(path, '&'.join(pairs))

        limit = page.paginator.per_page

        links = {
            'self': {
                'href': uri(path_format.format(page.number, limit)),
            },
            'base': {
                'href': uri(path),
            }
        }

        if page.has_previous():
            links['prev'] = {
                'href': uri(
                    path_format.format(page.previous_page_number(), limit)),
            }

        if page.has_next():
            links['next'] = {
                'href': uri(
                    path_format.format(page.next_page_number(), limit)),
            }

        return links
