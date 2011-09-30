from django.utils.timesince import timesince
from django.core.urlresolvers import reverse
from restlib import http, resources
from avocado.fields import logictree
from avocado.store.forms import ScopeForm, SessionScopeForm

__all__ = ('ScopeResource', 'SessionScopeResource', 'ScopeResourceCollection')

PATCH_OPERATIONS = ('add', 'remove')

class ScopeResource(resources.ModelResource):
    model = 'avocado.Scope'

    default_for_related = False

    fields = (':pk', 'name', 'description', 'store', 'count',
        'conditions', 'has_changed', 'timesince')

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
        scope = request.session['scope']

        # the requested object is the currently referenced by the session,
        # now we delete and deference
        if scope.references(pk):
            scope.reference.delete()
            scope.reference = None
            scope.save()
        else:
            target = self.queryset(request).filter(pk=pk)
            target.delete()

        # nothing to see..
        return http.NO_CONTENT

    def GET(self, request, pk):
        "Fetches a scope and sets the session scope to be a proxy."
        scope = request.session['scope']

        # if this object is already referenced by the session, simple return
        if scope.references(pk):
            return scope

        # attempt to fetch the requested object
        target = self.get(request, pk=pk)
        if not target:
            return http.NOT_FOUND

        # setup the reference on the session object, 
        target.reset(scope, exclude=('pk', 'reference', 'session'))
        scope.reference = target
        scope.commit()
        return scope

    def PUT(self, request, pk):
        "Explicitly updates an existing object given the request data."
        scope = request.session['scope']

        if scope.references(pk):
            target = scope.reference
        else:
            target = self.get(request, pk=pk)
            if not target:
                return http.NOT_FOUND

        form = ScopeForm(request.data, instance=target)

        if form.is_valid():
            target = form.save()
            # update the session to reflect the new changes
            target.reset(scope, exclude=('pk', 'reference', 'session'))
            scope.reference = target
            scope.commit()
            return target

        return form.errors


class SessionScopeResource(ScopeResource):
    default_for_related = True

    fields = (':pk', 'name', 'description', 'store', 'count',
        'condition_groups->conditions', 'has_changed', 'timesince', 'reference')

    @classmethod
    def _condition(self, json):
        text = logictree.transform(json).text

        j = ''
        if text.has_key('type'):
            j = ' %s ' % text['type']

        return {
            'concept_id': json['concept_id'],
            'condition': j.join(text['conditions'])
        }

    @classmethod
    def condition_groups(self, obj):
        if obj.store:
            if obj.store.has_key('children'):
                return map(self._condition, obj.store['children'])
            return [self._condition(obj.store)]

    @classmethod
    def reference(self, obj):
        if obj.reference:
            return {
                'id': obj.reference.pk,
                'url': reverse('api:scope:read', args=[obj.reference.pk]),
            }

    def GET(self, request):
        "Return this session's current perspective."
        return request.session['scope']

    def POST(self, request):
        json = request.data

        if not any(x in json for x in ('type', 'operator')):
            return http.BAD_REQUEST

        return self._condition(json)


    def PUT(self, request):
        "Explicitly updates an existing object given the request data."
        scope = request.session['scope']

        form = SessionScopeForm(request.data, instance=scope)

        if form.is_valid():
            form.save()
            return scope
        return form.errors


    def PATCH(self, request):
        """Adds support for incrementally updating the Scope store. It handles
        adding/removing a condition(s) for a single Concept.
        """
        scope = request.session['scope']

        if len(request.data) != 1:
            return http.UNPROCESSABLE_ENTITY

        operation, condition = request.data.items()[0]

        # both must exist to be processed
        if operation not in PATCH_OPERATIONS or not condition:
            return http.UNPROCESSABLE_ENTITY

        concept_id = condition['concept_id']

        # TODO this logic assumes concept conditions are only first-level
        # children. when concept conditions can be nested, this will need
        # to be more robust at checking
        if operation == 'remove':
            if not scope.store:
                return http.CONFLICT

            # denotes a logical operator node e.g. AND | OR.
            if scope.store.has_key('children'):
                for i, x in enumerate(iter(scope.store['children'])):
                    # TODO this logic assumes one condition per concept, update
                    # this once this is not the case
                    if x['concept_id'] == concept_id:
                        scope.store['children'].pop(i)
                        # move up the condition to the top node if it is the
                        # last one
                        if len(scope.store['children']) == 1:
                            scope.store = scope.store['children'][0]
                        break
                else:
                    return http.CONFLICT

            # standalone condition
            elif scope.store.get('concept_id') == concept_id:
                scope.store = None

            # a conflict in state between the client and the server
            else:
                return http.CONFLICT

        # add operations must check the validity and permission of the
        # requested content
        elif operation == 'add':
            # ensure the object is valid or fail
            if not scope.is_valid(condition):
                return http.UNPROCESSABLE_ENTITY

            # ensure the user has permission to make use of corresponding fields
            if not scope.has_permission(condition, request.user):
                return http.UNAUTHORIZED

            if not scope.store:
                scope.store = condition
            elif scope.store.has_key('children'):
                if filter(lambda x: x.get('concept_id', None) == concept_id,
                    scope.store['children']): return http.CONFLICT
                scope.store['children'].append(condition)
            else:
                scope.store = {'type': 'and', 'children': [scope.store, condition]}

        scope.save()
        return self._condition(condition)


class ScopeResourceCollection(resources.ModelResourceCollection):
    resource = ScopeResource
