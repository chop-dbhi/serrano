from django.utils.timesince import timesince
from django.core.urlresolvers import reverse
from restlib import http, resources
from avocado.store.forms import PerspectiveForm, SessionPerspectiveForm

__all__ = ('PerspectiveResource', 'SessionPerspectiveResource', 'PerspectiveResourceCollection')

class PerspectiveResource(resources.ModelResource):
    """The standard resource for perspectives. The API is currently limited to
    prevent overwriting of an existing perspective. Simple ``write`` operations
    targeting descriptive information (e.g. name) can be performed at any time.
    """
    model = 'avocado.Perspective'

    default_for_related = False

    fields = (':pk', 'name', 'description', 'keywords', 'timesince', 'modified')

    @classmethod
    def timesince(self, obj):
        if obj.modified:
            return '%s ago' % timesince(obj.modified)

    @classmethod
    def queryset(self, request):
        return self.model.objects.filter(user=request.user, session=False)

    def DELETE(self, request, pk):
        "Deletes a perspective and deferences the object from the session."
        session_obj = request.session['perspective']

        if session_obj.references(pk):
            session_obj.reference.delete()
            session_obj.reference = None
            session_obj.save()
        else:
            obj = self.queryset(request).filter(pk=pk)
            obj.delete()

        return http.NO_CONTENT

    def GET(self, request, pk):
        "Fetches a perspective and sets the session perspective to be a proxy."
        session_obj = request.session['perspective']
        # if this object is already referenced by the session, simple return
        if session_obj.references(pk):
            return session_obj.reference

        # attempt to fetch the requested object
        obj = self.get(request, pk=pk)
        if not obj:
            return http.NOT_FOUND
        # set the session object to be the proxy for the requested object and
        # perform a soft save to save off the reference.
        obj.reset(session_obj, exclude=('pk', 'session', 'reference'))
        session_obj.reference = obj
        session_obj.commit()

        return obj

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

        form = PerspectiveForm(request.data, instance=obj)

        if form.is_valid():
            saved_obj = form.save()
            saved_obj.reset(session_obj, exclude=('pk', 'session', 'reference'))
            session_obj.reference = saved_obj
            session_obj.commit()

            if saved_obj.pk is obj.pk:
                return obj

            headers = {'Location': reverse('api:perspectives:read', args=[saved_obj.pk])}
            return http.SEE_OTHER(**headers)

        return form.errors


class SessionPerspectiveResource(resources.ModelResource):
    model = 'avocado.Perspective'

    fields = (':pk', 'name', 'description', 'keywords', 'store', 'header',
        'has_changed', 'timesince', 'modified')

    @classmethod
    def timesince(self, obj):
        if obj.modified:
            return '%s ago' % timesince(obj.modified)

    def GET(self, request):
        "Return this session's current perspective."
        return request.session['perspective']

    def PUT(self, request):
        session_obj = request.session['perspective']
        data = request.data

        # see if the json object is only the ``store``
        if data.has_key('columns') or data.has_key('ordering'):
            data = {'store': data}

        store = data.get('store', None)

        if store is not None:
            if not session_obj.is_valid(store):
                return http.BAD_REQUEST
            if not session_obj.has_permission(store, request.user):
                return http.UNAUTHORIZED

        # checked if this session references an existing perspective. if so
        # the changes will be applied on the referenced object as a "soft"
        # save. the only caveat is if changes are pending and this request
        # changes the name. if this case, a new perspective is saved
        form = SessionPerspectiveForm(data, instance=session_obj)

        if form.is_valid():
            form.save()
            return session_obj

        return form.errors


class PerspectiveResourceCollection(resources.ModelResourceCollection):
    resource = PerspectiveResource

