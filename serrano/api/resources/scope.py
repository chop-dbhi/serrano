from django.utils.timesince import timesince
from django.core.urlresolvers import reverse
from restlib import http, resources
from avocado.fields import logictree
from avocado.store.forms import ScopeForm, SessionScopeForm
from serrano.cache import session_queue

__all__ = ('ScopeResource', 'SessionScopeResource', 'ScopeResourceCollection')

PATCH_OPERATIONS = ('add', 'remove', 'replace')

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
        instance = request.session['scope']

        # ensure to deference the session
        if instance.references(pk):
            instance.deference(delete=True)
            request.session['scope'] = instance
        else:
            reference = self.queryset(request).filter(pk=pk)
            reference.delete()

        # nothing to see..
        return http.NO_CONTENT

    def GET(self, request, pk):
        "Fetches a scope and sets the session scope to be a proxy."
        instance = request.session['scope']

        # if this object is already referenced by the session, simple return
        if not instance.references(pk):
            # attempt to fetch the requested object
            reference = self.get(request, pk=pk)
            if not reference:
                return http.NOT_FOUND

            reference.reset(instance)
            request.session['scope'] = instance
        else:
            reference = instance.reference

        return reference

    def PUT(self, request, pk):
        "Explicitly updates an existing object given the request data."
        instance = request.session['scope']

        if instance.references(pk):
            referenced = True
            reference = instance.reference
        else:
            referenced = False
            reference = self.get(request, pk=pk)
            if not reference:
                return http.NOT_FOUND

        form = ScopeForm(request.data, instance=reference)

        if form.is_valid():
            form.save()
            # if this is referenced by the session, update the session
            # instance to reflect this change. this only needs to be a
            # shallow reset since a PUT only updates local attributes
            if referenced:
                reference.reset(instance)
                request.session['scope'] = instance
            return reference

        return form.errors


class SessionScopeResource(ScopeResource):
    default_for_related = True

    fields = (':pk', 'name', 'description', 'store', 'count',
        'condition_groups->conditions', 'has_changed', 'timesince')

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
        groups = []
        if obj.store:
            if 'concept_id' not in obj.store:
                groups += map(self._condition, obj.store['children'])
            else:
                groups.append(self._condition(obj.store))
        return groups

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

    def PUT(self, request):
        "Explicitly updates an existing object given the request data."
        instance = request.session['scope']

        form = SessionScopeForm(request.data, instance=instance)

        if form.is_valid():
            # this may produce a new fork, so make sure we reset the session
            # instance if so
            new_instance = form.save()
            if instance != new_instance and not instance.references(new_instance.pk):
                new_instance.reset(instance)
            request.session['scope'] = instance
            return instance
        return form.errors

    def PATCH(self, request):
        """Adds support for incrementally updating the Scope store. It handles
        adding/removing a condition(s) for a single Concept.
        """
        with session_queue(request.session, key_prefix='scope-patch'):
            instance = request.session['scope']

            if len(request.data) != 1:
                return http.UNPROCESSABLE_ENTITY

            operation, condition = request.data.items()[0]

            # both must exist to be processed
            if operation not in PATCH_OPERATIONS or not condition:
                return http.UNPROCESSABLE_ENTITY

            concept_id = int(condition['concept_id'])

            # Make sure it is a valid structure..
            if not instance.is_valid(condition):
                return http.UNPROCESSABLE_ENTITY

            # Permission check..
            if not instance.has_permission(condition):
                return http.UNAUTHORIZED

            # XXX mad ghetto.. but better than whorking the session
            try:
                logictree.transform(condition).text
            except Exception:
                return http.UNPROCESSABLE_ENTITY

            # TODO this logic assumes concept conditions are only first-level
            # children. when concept conditions can be nested, this will need
            # to be more robust at checking
            if operation == 'remove' or operation == 'replace':
                if not instance.store:
                    return http.CONFLICT

                # standalone condition
                if 'concept_id' in instance.store:
                    if instance.store['concept_id'] == concept_id:
                        if operation == 'remove':
                            instance.store = None
                        else:
                            instance.store = condition
                    else:
                        return http.CONFLICT

                # denotes a logical operator node e.g. AND | OR.
                else:
                    for i, x in enumerate(instance.store['children']):
                        # TODO this logic assumes one condition per concept, update
                        # this once this is not the case
                        if x['concept_id'] == concept_id:
                            if operation == 'replace':
                                instance.store['children'][i] = condition
                                break
                            else:
                                instance.store['children'].pop(i)
                                # move up the condition to the top node if it is the
                                # last one
                                if len(instance.store['children']) == 1:
                                    instance.store = instance.store['children'][0]
                                break
                    else:
                        return http.CONFLICT

            # add operations must check the validity and permission of the
            # requested content
            elif operation == 'add':
                # ensure the object is valid or fail
                if not instance.is_valid(condition):
                    return http.UNPROCESSABLE_ENTITY

                # ensure the user has permission to make use of corresponding fields
                if not instance.has_permission(condition, request.user):
                    return http.UNAUTHORIZED

                if not instance.store:
                    instance.store = condition
                # top-level condition is part of a concept, nest the conditions
                elif 'concept_id' in instance.store:
                    if instance.store['concept_id'] != concept_id:
                        instance.store = {'type': 'and', 'children': [instance.store, condition]}
                    else:
                        return http.CONFLICT
                else:
                    if filter(lambda x: x['concept_id'] == concept_id, instance.store['children']):
                        return http.CONFLICT
                    instance.store['children'].append(condition)

            instance.save()
            request.session['scope'] = instance
            return self._condition(condition)


class ScopeResourceCollection(resources.ModelResourceCollection):
    resource = ScopeResource
