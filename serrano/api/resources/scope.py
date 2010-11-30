from django.http import HttpResponse
from restlib import http
from restlib.http import resources
from serrano.utils import uni2str

__all__ = ('ScopeResource', 'ScopeResourceCollection')

class ScopeResource(resources.ModelResource):
    model = 'avocado.Scope'

    def obj_to_dict(self, obj):
        return {
            'id': obj.id,
            'name': obj.name,
            'description': obj.description,
            'store': obj.store,
            'count': obj.cnt,
            'text': obj.get_text(),
        }

    def queryset(self, request):
        return self.model.objects.filter(user=request.user)

    def GET(self, request, pk):
        queryset = self.queryset(request)

        if pk == 'session':
            obj = request.session['report'].scope
        else:
            try:
                obj = queryset.get(pk=pk)
            except self.model.DoesNotExist:
                return HttpResponse(status=http.NOT_FOUND)
        return self.obj_to_dict(obj)

    def PUT(self, request, pk):
        """
        If the session's current ``scope`` is not temporary, it will be
        copied and store off temporarily.
        """
        # if the request is relative to the session and not to a specific id,
        # it cannot be assumed that if the session is using a saved scope
        # for it, iself, to be updated, but rather the session representation.
        # therefore, if the session scope is not temporary, make it a
        # temporary object with the new parameters.
        obj = request.session['report'].scope

        json = uni2str(request.data)

        # see if the json object is only the ``store``
        if 'children' in json or 'operator' in json:
            json = {'store': json}

        # assume the PUT request is only the store
        if pk != 'session':
            if pk != obj.id:
                try:
                    obj = self.queryset(request).get(pk=pk)
                except self.model.DoesNotExist:
                    return HttpResponse(status=http.NOT_FOUND)

        store = json.pop('store', None)

        if store is not None:
            # TODO improve this method of adding a partial condition tree
            if not obj.is_valid(store):
                return HttpResponse(status=http.BAD_REQUEST)
            if not obj.has_permission(store, request.user):
                return HttpResponse(status=http.UNAUTHORIZED)

            partial = store.pop('partial', False)
            obj.write(store, partial=partial)

        for k, v in json.iteritems():
            setattr(obj, k, v)

        # only save existing objances that have been saved.
        # a POST is required to make the initial save
        if obj.id is not None:
            obj.save()

        request.session.modified = True

        return 'OK'


class ScopeResourceCollection(resources.ModelResourceCollection):
    resource = ScopeResource()
