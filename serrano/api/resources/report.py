from datetime import datetime

from django.http import HttpResponse
from restlib import http
from restlib.http import resources

from serrano.http import ExcelResponse

__all__ = ('ReportResource', 'ReportResolverResource', 'ReportResourceCollection')

class ReportResource(resources.ModelResource):
    model = 'avocado.Report'
    fields = ('id', 'name', 'description')

    def queryset(self, request):
        return self.model.objects.filter(user=request.user)

    def GET(self, request, pk):
        queryset = self.queryset(request)

        if pk == 'session':
            obj = request.session['report']
        else:
            try:
                obj = queryset.get(pk=pk)
            except self.model.DoesNotExist:
                return HttpResponse(status=http.NOT_FOUND)
        return self.obj_to_dict(obj)


class ReportResourceCollection(resources.ModelResourceCollection):
    resource = ReportResource()
    fields = ('id', 'name', 'description')


class ReportResolverResource(ReportResource):
    def _export_csv(self, request, inst, *args, **kwargs):
        context = {'user': request.user}

        # fetch the report cache from the session, default to a new dict with
        # a few defaults. if a new dict is used, this implies that this a
        # report has not been resolved yet this session.
        cache = request.session.get(inst.REPORT_CACHE_KEY, {
            'timestamp': None,
            'page_num': 1,
            'per_page': 10,
            'offset': 0,
            'unique': None,
            'count': None,
            'datakey': inst.get_datakey(request)
        })

        # test if the cache is still valid, then attempt to fetch the requested
        # page from cache
        timestamp = cache['timestamp']
        queryset, unique, count = inst.get_queryset(timestamp, **context)

        rows = inst._execute_raw_query(queryset)
        iterator = inst.perspective.format(rows, 'csv')
        header = inst.perspective.get_columns_as_fields()
        name = 'audgendb_report-' + datetime.now().strftime('%Y-%m-%d-%H,%M,%S')

        return ExcelResponse(list(iterator), name, header)


    def GET(self, request, pk):
        "The interface for resolving a report, i.e. running a query."

        inst = request.session['report']

        if pk != 'session':
            if int(pk) != inst.id:
                try:
                    inst = self.queryset(request).get(pk=pk)
                except self.model.DoesNotExist:
                    return HttpResponse(status=http.NOT_FOUND)

        user = request.user

        if not inst.has_permission(user):
            return HttpResponse(status=http.FORBIDDEN)

        format_type = request.GET.get('f', None)

        if format_type == 'csv':
            return self._export_csv(request, inst, pk)

        page_num = request.GET.get('p', None)
        per_page = request.GET.get('n', None)

        count = unique = None

        # define the default context for use by ``get_queryset``
        # TODO can this be defined elsewhere? only scope depends on this, but
        # the user object has to propagate down from the view
        context = {'user': user}

        # fetch the report cache from the session, default to a new dict with
        # a few defaults. if a new dict is used, this implies that this a
        # report has not been resolved yet this session.
        cache = request.session.get(inst.REPORT_CACHE_KEY, {
            'timestamp': None,
            'page_num': 1,
            'per_page': 10,
            'offset': 0,
            'unique': None,
            'count': None,
            'datakey': inst.get_datakey(request)
        })

        # acts as reference to compare to so the resp can be determined
        old_cache = cache.copy()


        # test if the cache is still valid, then attempt to fetch the requested
        # page from cache
        timestamp = cache['timestamp']

        if inst.cache_is_valid(timestamp):
            # only update the cache if there are values specified for either arg
            if page_num:
                cache['page_num'] = int(page_num)
            if per_page:
                cache['per_page'] = int(per_page)

            rows = inst.get_page_from_cache(cache)

            # ``rows`` will only be None if no cache was found. attempt to
            # update the cache by running a partial query
            if rows is None:
                # since the cache is not invalid, the counts do not have to be run
                queryset, unique, count = inst.get_queryset(timestamp, **context)
                cache['timestamp'] = datetime.now()

                rows = inst.update_cache(cache, queryset);

        # when the cache becomes invalid, the cache must be refreshed
        else:
            queryset, unique, count = inst.get_queryset(timestamp, **context)

            cache.update({
                'timestamp': datetime.now(),
                'page_num': 1,
                'offset': 0,
            })

            if count is not None:
                cache['count'] = count
                if unique is not None:
                    cache['unique'] = unique

            rows = inst.refresh_cache(cache, queryset)


        request.session[inst.REPORT_CACHE_KEY] = cache

        # the response is composed of a few different data that is dependent on
        # various conditions. the only required data is the ``rows`` which will
        # always be needed since all other components act on determing the rows
        # to be returned
        resp = {
            'rows': list(inst.perspective.format(rows, 'html')),
        }

        # a *no change* requests implies the page has been requested statically
        # and the whole response object must be provided
        resp.update({
            'per_page': cache['per_page'],
            'count': cache['count'],
            'unique': cache['unique'],
        })

        paginator, page = inst.paginator_and_page(cache)

        if paginator.num_pages > 1:
            resp.update({
                'pages': {
                    'page': page.number,
                    'pages': page.page_links(),
                    'num_pages': paginator.num_pages,
                }
            })

        return resp
