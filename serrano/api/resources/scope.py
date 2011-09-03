from django.utils.timesince import timesince
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from restlib import http, resources
from avocado.store.forms import ScopeForm, SessionScopeForm

__all__ = ('ScopeResource', 'SessionScopeResource', 'ScopeResourceCollection')

class ScopeResource(resources.ModelResource):
    model = 'avocado.Scope'

    default_for_related = False

    fields = (':pk', 'name', 'description', 'store', 'cnt->count',
        'get_text->text', 'has_changed', 'timesince')

    middleware = (
        'serrano.api.middleware.NeverCache',
    ) + resources.Resource.middleware

    @classmethod
    def timesince(self, obj):
        if obj.modified:
            return '%s ago' % timesince(obj.modified)

    @classmethod
    def queryset(self, request):
        return self.model._default_manager.filter(user=request.user)

    def DELETE(self, request, pk):
        session_obj = request.session['report'].scope

        if session_obj.get_reference_pk() == int(pk):
            session_obj.reference.delete()
            session_obj.reference = None
            request.session.modified = True
        else:
            obj = self.queryset(request).filter(pk=pk)
            obj.delete()

        return http.NO_CONTENT

    def GET(self, request, pk):
        "Fetches a scope and sets the session scope to be a proxy."
        session_obj = request.session['report'].scope
        # if this object is already referenced by the session, simple return
        if session_obj.get_reference_pk() == int(pk):
            return session_obj

        # attempt to fetch the requested object
        obj = self.get(request, pk=pk)
        if not obj:
            return http.NOT_FOUND

        # set the session object to be the proxy for the requested object and
        # perform a soft save to save off the reference.
        session_obj.proxy(obj)
        session_obj.save()

        request.session.modified = True
        return session_obj

    def PUT(self, request, pk):
        "Explicitly updates an existing object given the request data."
        session_obj = request.session['report'].scope

        if session_obj.get_reference_pk() == int(pk):
            obj = session_obj.reference
        else:
            obj = self.get(request, pk=pk)
            if not obj:
                return http.NOT_FOUND

        form = ScopeForm(request.data, instance=obj)

        if form.is_valid():
            saved_obj = form.save()
            # set the session object to be the proxy for the requested object and
            # perform a soft save to save off the reference.
            session_obj.proxy(saved_obj)
            session_obj.save()

            request.session.modified = True
            # if this is not a new object, simply return the object, otherwise
            # redirect to the new object
            if saved_obj.pk is obj.pk:
                return obj

            headers = {'Location': reverse('api:scope:read', args=[saved_obj.pk])}
            return http.SEE_OTHER(**headers)

        return form.errors


class SessionScopeResource(ScopeResource):
    default_for_related = True

    def GET(self, request):
        "Return this session's current perspective."
        return request.session['report'].scope

    def PUT(self, request):
        "Explicitly updates an existing object given the request data."
        session_obj = request.session['report'].scope

        form = SessionScopeForm(request.data, instance=session_obj)

        if form.is_valid():
            form.save()
            return session_obj
        return form.errors


class ScopeResourceCollection(resources.ModelResourceCollection):
    resource = ScopeResource
