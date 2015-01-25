from django.db.models.query import QuerySet
from django.core.cache import cache
from django.core.paginator import Paginator
from avocado.core.cache import cache_key
from avocado.conf import settings
from restlib2.params import Parametizer, IntParam
from restlib2.resources import Resource

__all__ = ('PaginatorResource', 'PaginatorParametizer')


def _count(s):
    if isinstance(s, QuerySet):
        return s.count()

    return len(s)


class PaginatorParametizer(Parametizer):
    page = IntParam(1)
    limit = IntParam(20)


class PaginatorResource(Resource):
    parametizer = PaginatorParametizer

    def get_paginator(self, queryset, limit):
        paginator = Paginator(queryset, per_page=limit)
        paginator.has_limit = bool(limit)

        # Cache count for paginator to prevent redundant calls between requests
        if settings.DATA_CACHE_ENABLED:
            key = cache_key('paginator', kwargs={
                'queryset': queryset
            })

            count = cache.get(key)

            if count is None:
                count = _count(queryset)
                cache.set(key, count)
        else:
            count = _count(queryset)

        paginator._count = count

        if not limit:
            # Prevent division by zero error in case count is zero
            paginator.per_page = max(count, 1)

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
            'self': uri(path_format.format(page=page.number, limit=limit)),
            'base': uri(path),
            'first': uri(path_format.format(page=1, limit=limit)),
            'last': uri(path_format.format(
                page=page.paginator.num_pages, limit=limit)),
        }

        if page.has_previous():
            links['prev'] = uri(path_format.format(
                page=page.previous_page_number(), limit=limit))

        if page.has_next():
            links['next'] = uri(path_format.format(
                page=page.next_page_number(), limit=limit))

        return links

    def get_page_response(self, request, paginator, page):
        return {
            'count': paginator.count,
            'limit': paginator.per_page if paginator.has_limit else 0,
            'num_pages': paginator.num_pages,
            'page_num': page.number,
        }
