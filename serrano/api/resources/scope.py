from restlib import http, resources
from serrano.utils import uni2str

__all__ = ('ScopeResource', 'ScopeResourceCollection')

class ScopeResource(resources.ModelResource):
    model = 'avocado.Scope'

    fields = (':pk', 'name', 'description', 'store', 'cnt->count',
        'get_text->text')

    middleware = (
        'serrano.api.middleware.NeverCache',
    ) + resources.Resource.middleware

    @classmethod
    def queryset(self, request):
        return self.model._default_manager.filter(user=request.user)

    def GET(self, request, pk):
        queryset = self.queryset(request)

        if pk == 'session':
            obj = request.session['report'].scope
        else:
            obj = self.get(request, pk=pk)
            if not obj:
                return http.NOT_FOUND

        return obj

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
                obj = self.get(request, pk=pk)
                if not obj:
                    return http.NOT_FOUND

        store = json.pop('store', None)

        if store is not None:
            # TODO improve this method of adding a partial condition tree
            if not obj.is_valid(store):
                return http.BAD_REQUEST
            if not obj.has_permission(store, request.user):
                return http.UNAUTHORIZED

            partial = store.pop('partial', False)
            obj.write(store, partial=partial)

        for k, v in json.iteritems():
            setattr(obj, k, v)

        # only save existing objances that have been saved.
        # a POST is required to make the initial save
        if obj.id is not None:
            obj.save()

        request.session.modified = True

        return ''


class ScopeResourceCollection(resources.ModelResourceCollection):
    resource = ScopeResource
