import functools

from preserialize.serialize import serialize
from restlib2.http import codes

from avocado.models import DataQuery
from serrano.links import reverse_tmpl
from serrano.resources import templates
from serrano.resources.query.base import query_posthook, QueryBase


class QueryForksResource(QueryBase):
    "Resource for accessing forks of the specified query or forking the query"
    template = templates.ForkedQuery

    def is_not_found(self, request, response, **kwargs):
        return self.get_object(request, **kwargs) is None

    def get_link_templates(self, request):
        uri = request.build_absolute_uri

        return {
            'self': reverse_tmpl(
                uri, 'serrano:queries:single', {'pk': (int, 'id')}),
            'parent': reverse_tmpl(
                uri, 'serrano:queries:single', {'pk': (int, 'parent_id')}),
        }

    def get_queryset(self, request, **kwargs):
        instance = self.get_object(request, **kwargs)
        return self.model.objects.filter(parent=instance.pk)

    def get_object(self, request, pk=None, **kwargs):
        if not pk:
            raise ValueError('A pk must be used for the fork lookup')

        if not hasattr(request, 'instance'):
            try:
                instance = self.model.objects.get(pk=pk)
            except self.model.DoesNotExist:
                instance = None

            request.instance = instance

        return request.instance

    def prepare(self, request, instance, template=None):
        if template is None:
            template = self.template

        return serialize(instance, **template)

    def _requestor_can_get_forks(self, request, instance):
        """
        A user can retrieve the forks of a query if that query is public or
        if they are the owner of that query.
        """
        if instance.public:
            return True

        if not getattr(request, 'user', None):
            return False

        return (request.user.is_authenticated() and
                request.user == instance.user)

    def _requestor_can_fork(self, request, instance):
        """
        A user can fork a query if that query is public or if they are the
        owner or in the shared_users group of that query.
        """
        if instance.public:
            return True

        if getattr(request, 'user', None) and request.user.is_authenticated():
            return (request.user == instance.user or
                    instance.shared_users.filter(pk=request.user.pk).exists())

        return False

    def get(self, request, **kwargs):
        instance = self.get_object(request, **kwargs)

        if self._requestor_can_get_forks(request, instance):
            return self.prepare(request, self.get_queryset(request, **kwargs))

        data = {
            'message': 'Cannot access forks',
        }
        return self.render(request, data, status=codes.unauthorized)

    def post(self, request, **kwargs):
        instance = self.get_object(request, **kwargs)

        if self._requestor_can_fork(request, instance):
            fork = DataQuery(name=instance.name,
                             description=instance.description,
                             view_json=instance.view_json,
                             context_json=instance.context_json,
                             parent=instance)

            if getattr(request, 'user', None):
                fork.user = request.user
            elif request.session.session_key:
                fork.session_key = request.session.session_key

            fork.save()
            request.session.modified = True

            posthook = functools.partial(query_posthook, request=request)
            data = serialize(fork, posthook=posthook, **templates.Query)

            return self.render(request, data, status=codes.created)

        data = {
            'message': 'Cannot fork query',
        }
        return self.render(request, data, status=codes.unauthorized)
