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
        paginator = Paginator(queryset, per_page=limit)
        paginator.has_limit = bool(limit)

        # Perform count an update paginator to prevent redundant call
        if not limit:
            count = len(queryset)
            paginator.per_page = count
            paginator._count = count

        return paginator

    def get_page_links(self, request, path, page, extra=None):
        "Returns the page links."
        uri = request.build_absolute_uri

        # format string will be expanded below
        if page.paginator.has_limit:
            limit = page.paginator.per_page
            params = {
                'limit': '{limit}',
                'page': '{page}',
            }
        else:
            limit = None
            params = {
                'limit': '0',
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

        links = {
            'self': {
                'href': uri(path_format.format(page=page.number,
                                               limit=limit)),
            },
            'base': {
                'href': uri(path),
            }
        }

        if page.has_previous():
            links['prev'] = {
                'href': uri(
                    path_format.format(page=page.previous_page_number(),
                                       limit=limit)),
            }

        if page.has_next():
            links['next'] = {
                'href': uri(
                    path_format.format(page=page.next_page_number(),
                                       limit=limit)),
            }

        return links

    def get_page_response(self, request, paginator, page):
        return {
            'count': paginator.count,
            'limit': paginator.per_page if paginator.has_limit else 0,
            'num_pages': paginator.num_pages,
            'page_num': page.number,
        }
