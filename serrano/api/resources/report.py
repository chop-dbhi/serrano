from datetime import datetime
from django.utils.timesince import timesince
from django.core.urlresolvers import reverse
from avocado.store.forms import ReportForm, SessionReportForm
from restlib import http, resources
from serrano.http import ExcelResponse

__all__ = ('ReportResource', 'SessionReportResource', 'ReportResourceCollection',
    'ReportRedirectResource')

class ReportResource(resources.ModelResource):
    model = 'avocado.Report'

    fields = (':pk', 'name', 'description', 'modified', 'timesince',
        'has_changed', 'count', 'unique_count', 'url', 'permalink',
        'model_name', 'model_name_plural')

    default_for_related = False

    middleware = (
        'serrano.api.middleware.NeverCache',
    ) + resources.Resource.middleware

    @classmethod
    def unique_count(self, obj):
        return obj.scope.count

    @classmethod
    def timesince(self, obj):
        if obj.modified:
            return '%s ago' % timesince(obj.modified)

    @classmethod
    def url(self, obj):
        return reverse('api:reports:read', args=[obj.pk])

    @classmethod
    def permalink(self, obj):
        return reverse('report-redirect', args=[obj.pk])

    @classmethod
    def queryset(self, request):
        return self.model._default_manager.filter(user=request.user,
            session=False).order_by('-modified')

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

    def _GET(self, request, instance):
        "The interface for resolving a report, i.e. running a query."
        user = request.user

        if not instance.has_permission(user):
            return http.FORBIDDEN

        format_type = request.GET.get('format', None)

        # XXX: hack
        if format_type == 'csv':
            return self._export_csv(request, instance)

        page_num = request.GET.get('page', None)
        per_page = request.GET.get('size', None)

        count = unique = None

        # define the default context for use by ``get_queryset``
        # TODO can this be defined elsewhere? only scope depends on this, but
        # the user object has to propagate down from the view
        context = {'user': user}

        # fetch the report cache from the session, default to a new dict with
        # a few defaults. if a new dict is used, this implies that this a
        # report has not been resolved yet this session.
        cache = request.session.get(instance.REPORT_CACHE_KEY, {
            'timestamp': None,
            'page_num': 1,
            'per_page': 10,
            'offset': 0,
            'unique': None,
            'count': None,
            'datakey': instance.get_datakey(request)
        })

        # test if the cache is still valid, then attempt to fetch the requested
        # page from cache
        timestamp = cache['timestamp']

        if instance.cache_is_valid(timestamp):
            # only update the cache if there are values specified for either arg
            if page_num:
                cache['page_num'] = int(page_num)
            if per_page:
                cache['per_page'] = int(per_page)

            rows = instance.get_page_from_cache(cache)

            # ``rows`` will only be None if no cache was found. attempt to
            # update the cache by running a partial query
            if rows is None:
                # since the cache is not invalid, the counts do not have to be run
                queryset, unique, count = instance.get_queryset(timestamp, **context)
                cache['timestamp'] = datetime.now()

                rows = instance.update_cache(cache, queryset);

        # when the cache becomes invalid, the cache must be refreshed
        else:
            queryset, unique, count = instance.get_queryset(timestamp, **context)

            cache.update({
                'timestamp': datetime.now(),
                'page_num': 1,
                'offset': 0,
            })

            if count is not None:
                cache['count'] = count
                if unique is not None:
                    cache['unique'] = unique

            rows = instance.refresh_cache(cache, queryset)


        request.session[instance.REPORT_CACHE_KEY] = cache

        # the response is composed of a few different data that is dependent on
        # various conditions. the only required data is the ``rows`` which will
        # always be needed since all other components act on determing the rows
        # to be returned
        resp = {
            'rows': list(instance.perspective.format(rows, 'html')),
        }

        if instance.name:
            resp['name'] = instance.name

        if instance.description:
            resp['description'] = instance.description

        # a *no change* requests implies the page has been requested statically
        # and the whole response object must be provided
        resp.update({
            'per_page': cache['per_page'],
            'count': cache['count'],
            'unique': cache['unique'],
        })

        paginator, page = instance.paginator_and_page(cache)

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
        instance = request.session['report']

        # ensure to deference the session
        if instance.references(pk):
            instance.deference(delete=True)
            request.session['report'] = instance
        else:
            reference = self.queryset(request).filter(pk=pk)
            reference.delete()

        return http.NO_CONTENT

    def GET(self, request, pk):
        instance = request.session['report']
        # if this object is already referenced by the session, simple return
        if not instance.references(pk):
            # attempt to fetch the requested object
            reference = self.get(request, pk=pk)
            if not reference:
                return http.NOT_FOUND

            reference.reset(instance)
            request.session['report'] = instance
        else:
            reference = instance.reference

        # XXX: hackity hack..
        if request.GET.has_key('data'):
            return self._GET(request, reference)

        return reference

    def PUT(self, request, pk):
        "Explicitly updates an existing object given the request data."
        instance = request.session['report']

        if instance.references(pk):
            referenced = True
            reference = instance.reference
        else:
            referenced = False
            reference = self.get(request, pk=pk)
            if not reference:
                return http.NOT_FOUND

        form = ReportForm(request.data, instance=reference)

        if form.is_valid():
            form.save()
            # if this is referenced by the session, update the session
            # instance to reflect this change. this only needs to be a
            # shallow reset since a PUT only updates local attributes
            if referenced:
                reference.reset(instance)
                request.session['report'] = instance
            return reference

        return form.errors


class SessionReportResource(ReportResource):
    "Handles making requests to and from the session's report object."

    fields = (':pk', 'name', 'description', 'modified', 'timesince',
        'has_changed', 'count', 'unique_count', 'permalink', 'reference_id',
        'scope', 'perspective', 'model_name', 'model_name_plural')

    @classmethod
    def reference_id(self, obj):
        if obj.reference:
            return obj.reference.pk

    @classmethod
    def permalink(self, obj):
        if obj.reference:
            return reverse('report-redirect', args=[obj.reference.pk])

    def GET(self, request):
        instance = request.session['report']
        if request.GET.has_key('data'):
            return self._GET(request, instance)
        return instance

    def PUT(self, request):
        instance = request.session['report']

        # A temporary shorthand for reverting the state of the session
        # object with a reference. This will revert any unsaved changed
        # back to the state of the reference.
        if request.data.has_key('revert'):
            if not instance.reference:
                return http.CONFLICT
            instance.reference.reset(instance)
            request.session['report'] = instance
            return instance

        form = SessionReportForm(request.data, instance=instance)

        if form.is_valid():
            reference = form.save()
            # this may produce a new fork, so make sure we reset if so
            if instance != reference and not instance.references(reference.pk):
                reference.reset(instance)
            request.session['report'] = instance
            return instance
        return form.errors


class SimpleReportResource(ReportResource):
    default_for_related = True


class ReportResourceCollection(resources.ModelResourceCollection):
    resource = SimpleReportResource

    def GET(self, request):
        return self.queryset(request)

    def POST(self, request):
        _pk = request.data.pop('_id', None)
        if not _pk:
            return http.UNPROCESSABLE_ENTITY

        reference = self.get(request, pk=_pk)
        if not reference:
            return http.CONFLICT

        instance = reference.fork(commit=False)
        # this form data only applies to the report object
        form = ReportForm(request.data, instance=instance)

        if form.is_valid():
            # halt the typical save, use the fork `commit' instead
            form.save(commit=False)
            instance.commit()
            return instance
        return form.errors


class ReportRedirectResource(ReportResource):

    def GET(self, request, pk):
        instance = request.session['report']
        # if this object is already referenced by the session, simple return
        if not instance.references(pk):
            # attempt to fetch the requested object
            reference = self.get(request, pk=pk)
            if not reference:
                return http.NOT_FOUND

            reference.reset(instance)
            request.session['report'] = instance

        return http.SEE_OTHER(location=reverse('report'))

