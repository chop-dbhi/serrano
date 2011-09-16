from datetime import datetime
from django.utils.timesince import timesince
from django.core.urlresolvers import reverse
from avocado.store.forms import ReportForm, SessionReportForm
from restlib import http, resources
from serrano.http import ExcelResponse

__all__ = ('ReportResource', 'SessionReportResource', 'ReportResourceCollection')

class ReportResource(resources.ModelResource):
    model = 'avocado.Report'

    fields = (':pk', 'name', 'description', 'modified', 'timesince', 'has_changed')

    default_for_related = False

    middleware = (
        'serrano.api.middleware.NeverCache',
    ) + resources.Resource.middleware

    @classmethod
    def timesince(self, obj):
        if obj.modified:
            return '%s ago' % timesince(obj.modified)

    @classmethod
    def queryset(self, request):
        return self.model._default_manager.filter(user=request.user, session=False)

    def _export_csv(self, request, inst):
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
        name = 'report-' + datetime.now().strftime('%Y-%m-%d-%H,%M,%S')

        return ExcelResponse(list(iterator), name, header)

    def _GET(self, request, inst):
        "The interface for resolving a report, i.e. running a query."
        user = request.user

        if not inst.has_permission(user):
            return http.FORBIDDEN

        format_type = request.GET.get('f', None)

        # XXX: hack
        if format_type == 'csv':
            return self._export_csv(request, inst)

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

        if inst.name:
            resp['name'] = inst.name

        if inst.description:
            resp['description'] = inst.description

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

    def DELETE(self, request, pk):
        session_obj = request.session['report']

        if session_obj.references(pk):
            session_obj.reference.delete()
            session_obj.reference = None
            session_obj.save()
        else:
            obj = self.queryset(request).filter(pk=pk)
            obj.delete()

        return http.NO_CONTENT

    def GET(self, request, pk):
        session_obj = request.session['report']
        # if this object is already referenced by the session, simple return
        if not session_obj.references(pk):
            # attempt to fetch the requested object
            obj = self.get(request, pk=pk)
            if not obj:
                return http.NOT_FOUND
            # set the session object to be the proxy for the requested object and
            # perform a soft save to save off the reference.
            obj.scope.reset(session_obj.scope, exclude=('pk', 'session', 'reference'))
            session_obj.scope.reference = obj.scope
            session_obj.scope.commit()

            obj.perspective.reset(session_obj.perspective, exclude=('pk', 'session', 'reference'))
            session_obj.perspective.reference = obj.perspective
            session_obj.perspective.commit()

            obj.reset(session_obj, exclude=('pk', 'session', 'reference'))
            session_obj.reference = obj
            session_obj.commit()

        if request.GET.has_key('data'):
            return self._GET(request, session_obj)
        return session_obj


    def PUT(self, request, pk):
        """Explicitly updates an existing object given the request data. The
        data that can be updated via the request is limited to simple
        description data. Note, that if there are any pending changes applied
        via the session, these will be saved as well.
        """
        session_obj = request.session['report']
        if session_obj.references(pk):
            obj = session_obj.reference
        else:
            obj = self.get(request, pk=pk)
            if not obj:
                return http.NOT_FOUND
            session_obj = None

        form = ReportForm(data=request.data, instance=session_obj)

        if form.is_valid():
            saved_obj = form.save()
            if saved_obj.pk is obj.pk:
                return obj

            headers = {'Location': reverse('api:reports:read', args=[saved_obj.pk])}
            return http.SEE_OTHER(**headers)

        return form.errors



class SessionReportResource(ReportResource):
    "Handles making requests to and from the session's report object."

    def GET(self, request):
        session_obj = request.session['report']
        if request.GET.has_key('data'):
            return self._GET(request, session_obj)
        return session_obj

    def PUT(self, request):
        session_obj = request.session['report']
        form = SessionReportForm(request.data, instance=session_obj)

        if form.is_valid():
            form.save()
            return session_obj
        return form.errors


class SimpleReportResource(ReportResource):
    default_for_related = True


class ReportResourceCollection(resources.ModelResourceCollection):
    resource = SimpleReportResource

    def GET(self, request):
        return self.queryset(request)

