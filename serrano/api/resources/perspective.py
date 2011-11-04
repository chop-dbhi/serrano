from django.utils.timesince import timesince
from restlib import http, resources
from avocado.store.forms import PerspectiveForm, SessionPerspectiveForm

__all__ = ('PerspectiveResource', 'SessionPerspectiveResource', 'PerspectiveResourceCollection')

PATCH_OPERATIONS = ('add', 'remove', 'replace')

class PerspectiveResource(resources.ModelResource):
    """The standard resource for perspectives. The API is currently limited to
    prevent overwriting of an existing perspective. Simple ``write`` operations
    targeting descriptive information (e.g. name) can be performed at any time.
    """
    model = 'avocado.Perspective'

    default_for_related = False

    fields = (':pk', 'name', 'description', 'keywords', 'timesince', 'modified')

    middleware = (
        'serrano.api.middleware.NeverCache',
    ) + resources.Resource.middleware

    @classmethod
    def timesince(self, obj):
        if obj.modified:
            return '%s ago' % timesince(obj.modified)

    @classmethod
    def queryset(self, request):
        return self.model.objects.filter(user=request.user, session=False)

    def DELETE(self, request, pk):
        "Deletes a perspective and deferences the object from the session."
        instance = request.session['perspective']

        # ensure to deference the session
        if instance.references(pk):
            instance.deference(delete=True)
            request.session['perspective'] = instance
        else:
            reference = self.queryset(request).filter(pk=pk)
            reference.delete()

        # nothing to see..
        return http.NO_CONTENT

    def GET(self, request, pk):
        "Fetches a perspective and sets the session perspective to be a proxy."
        instance = request.session['perspective']

        # if this object is already referenced by the session, simple return
        if not instance.references(pk):
            # attempt to fetch the requested object
            reference = self.get(request, pk=pk)
            if not reference:
                return http.NOT_FOUND

            reference.reset(instance)
            request.session['perspective'] = instance
        else:
            reference = instance.reference

        return reference

    def PUT(self, request, pk):
        """Explicitly updates an existing object given the request data. The
        data that can be updated via the request is limited to simple
        description data. Note, that if there are any pending changes applied
        via the session, these will be saved as well.
        """
        instance = request.session['perspective']

        if instance.references(pk):
            referenced = True
            reference = instance.reference
        else:
            referenced = False
            reference = self.get(request, pk=pk)
            if not reference:
                return http.NOT_FOUND

        form = PerspectiveForm(request.data, instance=reference)

        if form.is_valid():
            form.save()
            # if this is referenced by the session, update the session
            # instance to reflect this change. this only needs to be a
            # shallow reset since a PUT only updates local attributes
            if referenced:
                reference.reset(instance)
                request.session['perspective'] = instance
            return reference

        return form.errors


class SessionPerspectiveResource(PerspectiveResource):
    model = 'avocado.Perspective'

    fields = (':pk', 'name', 'description', 'keywords', 'read->store', 'header',
        'has_changed', 'timesince', 'modified')

    default_for_related = True

    @classmethod
    def timesince(self, obj):
        if obj.modified:
            return '%s ago' % timesince(obj.modified)

    def GET(self, request):
        "Return this session's current perspective."
        return request.session['perspective']

    def PUT(self, request):
        "Explicitly updates an existing object given the request data."
        instance = request.session['perspective']
        data = request.data

        # see if the json object is only the ``store``
        if data.has_key('columns') or data.has_key('ordering'):
            data = {'store': data}

        store = data.get('store', None)

        if store is not None:
            if not instance.is_valid(store):
                return http.BAD_REQUEST
            if not instance.has_permission(store, request.user):
                return http.UNAUTHORIZED

        # checked if this session references an existing perspective. if so
        # the changes will be applied on the referenced object as a "soft"
        # save. the only caveat is if changes are pending and this request
        # changes the name. if this case, a new perspective is saved
        form = SessionPerspectiveForm(data, instance=instance)

        if form.is_valid():
            # this may produce a new fork, so make sure we reset the session
            # instance if so
            new_instance = form.save()
            if instance != new_instance and not instance.references(new_instance.pk):
                new_instance.reset(instance)
            request.session['perspective'] = instance
            return instance
        return form.errors

    def PATCH(self, request):
        instance = request.session['perspective']

        if len(request.data) != 1:
            return http.UNPROCESSABLE_ENTITY

        # XXX: until we move to the jsonpatch library..
        if not request.data.has_key('replace'):
            return http.UNPROCESSABLE_ENTITY

        store = request.data['replace']

        if store is not None:
            if not instance.is_valid({'store': store}):
                return http.BAD_REQUEST
            if not instance.has_permission({'store': store}, request.user):
                return http.UNAUTHORIZED

        instance.write(store)
        instance.save()
        request.session['perspective'] = instance
        return instance

class PerspectiveResourceCollection(resources.ModelResourceCollection):
    resource = PerspectiveResource

