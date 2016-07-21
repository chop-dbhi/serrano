from __future__ import unicode_literals
from datetime import datetime
import functools

from django.db.models import Q
from django.conf import settings
from modeltree.tree import trees, MODELTREE_DEFAULT_ALIAS
from preserialize.serialize import serialize
from restlib2.http import codes
from restlib2.params import Parametizer, StrParam

from avocado.events import usage
from avocado.models import DataQuery, DataView, DataContext
from avocado.query import pipeline
from serrano.forms import QueryForm
from serrano.links import reverse_tmpl
from serrano.resources import templates
from serrano.resources.base import ThrottledResource
from serrano.utils import send_mail


DELETE_QUERY_EMAIL_TITLE = "'{0}' has been deleted"
DELETE_QUERY_EMAIL_BODY = """The query named '{0}' has been deleted. You are
 being notified because this query was shared with you. This query is no
 longer available."""


def query_posthook(instance, data, request):
    if getattr(instance, 'user', None) and instance.user.is_authenticated():
        data['is_owner'] = instance.user == request.user
    else:
        data['is_owner'] = instance.session_key == request.session.session_key

    if not data['is_owner']:
        del data['shared_users']

    return data


class QueryParametizer(Parametizer):
    tree = StrParam(MODELTREE_DEFAULT_ALIAS, choices=trees)
    processor = StrParam('default', choices=pipeline.query_processors)


class QueryBase(ThrottledResource):
    cache_max_age = 0
    private_cache = True

    model = DataQuery
    template = templates.Query

    parametizer = QueryParametizer

    def prepare(self, request, instance, template=None):
        if template is None:
            template = self.template
        posthook = functools.partial(query_posthook, request=request)
        return serialize(instance, posthook=posthook, **template)

    def get_link_templates(self, request):
        uri = request.build_absolute_uri

        return {
            'self': reverse_tmpl(
                uri, 'serrano:queries:single', {'pk': (int, 'id')}),
            'forks': reverse_tmpl(
                uri, 'serrano:queries:forks', {'pk': (int, 'id')}),
            'stats': reverse_tmpl(
                uri, 'serrano:queries:stats', {'pk': (int, 'id')}),
            'results': reverse_tmpl(
                uri, 'serrano:queries:results', {'pk': (int, 'id')}),
        }

    def get_queryset(self, request, **kwargs):
        "Constructs a QuerySet for this user or session."

        if getattr(request, 'user', None) and request.user.is_authenticated():
            kwargs['user'] = request.user
        elif request.session.session_key:
            kwargs['session_key'] = request.session.session_key
        else:
            # The only case where kwargs is empty is for non-authenticated
            # cookieless agents.. e.g. bots, most non-browser clients since
            # no session exists yet for the agent.
            return self.model.objects.none()

        return self.model.objects.filter(**kwargs)

    def get_request_filters(self, request):
        filters = {}

        if getattr(request, 'user', None) and request.user.is_authenticated():
            filters['user'] = request.user
        elif request.session.session_key:
            filters['session_key'] = request.session.session_key

        return filters

    def get_object(self, request, pk=None, session=None, **kwargs):
        if not pk and not session:
            raise ValueError('A pk or session must used for the lookup')

        if not hasattr(request, 'instance'):
            queryset = self.get_queryset(request, **kwargs)
            instance = None

            try:
                if pk:
                    instance = queryset.get(pk=pk)
                else:
                    instance = queryset.get(session=True)
            except self.model.DoesNotExist:
                if session:
                    filters = self.get_request_filters(request)

                    try:
                        context = DataContext.objects.filter(**filters)\
                            .get(session=True)
                        view = DataView.objects.filter(**filters)\
                            .get(session=True)
                        instance = DataQuery(context_json=context.json,
                                             view_json=view.json)
                    except (DataContext.DoesNotExist, DataView.DoesNotExist):
                        pass

            request.instance = instance

        return request.instance


class QueriesResource(QueryBase):
    "Resource for accessing the queries a shared with or owned by a user"
    template = templates.Query

    def prepare(self, request, instance, template=None):
        if template is None:
            template = self.template
        posthook = functools.partial(query_posthook, request=request)
        return serialize(instance, posthook=posthook, **template)

    def get_queryset(self, request, **kwargs):
        if getattr(request, 'user', None) and request.user.is_authenticated():
            f = Q(user=request.user) | Q(shared_users__pk=request.user.pk)
        elif request.session.session_key:
            f = Q(session_key=request.session.session_key)
        else:
            return super(QueriesResource, self).get_queryset(request, **kwargs)
        return self.model.objects.filter(f, **kwargs) \
            .order_by('-accessed').distinct()

    def get(self, request):
        queryset = self.get_queryset(request)
        return self.prepare(request, queryset)

    def post(self, request):
        form = QueryForm(request, request.data)

        if form.is_valid():
            instance = form.save()
            usage.log('create', instance=instance, request=request)
            request.session.modified = True
            response = self.render(request, self.prepare(request, instance),
                                   status=codes.created)
        else:
            data = {
                'message': 'Error creating query',
                'errors': dict(form.errors),
            }
            response = self.render(request, data,
                                   status=codes.unprocessable_entity)
        return response


class PublicQueriesResource(QueryBase):
    "Resource for accessing public queries"
    template = templates.BriefQuery

    def prepare(self, request, instance, template=None):
        if template is None:
            template = self.template

        posthook = functools.partial(query_posthook, request=request)
        return serialize(instance, posthook=posthook, **template)

    def get_queryset(self, request, **kwargs):
        kwargs['public'] = True

        return self.model.objects.filter(**kwargs).order_by('-accessed') \
            .distinct()

    def get(self, request):
        queryset = self.get_queryset(request)
        return self.prepare(request, queryset)


class QueryResource(QueryBase):
    "Resource for accessing a single query"
    def is_not_found(self, request, response, **kwargs):
        return self.get_object(request, **kwargs) is None

    def get(self, request, **kwargs):
        instance = self.get_object(request, **kwargs)
        usage.log('read', instance=instance, request=request)

        self.model.objects.filter(pk=instance.pk).update(
            accessed=datetime.now())

        return self.prepare(request, instance)

    def put(self, request, **kwargs):
        instance = self.get_object(request, **kwargs)

        form = QueryForm(request, request.data, instance=instance)

        if form.is_valid():
            instance = form.save()
            usage.log('update', instance=instance, request=request)
            request.session.modified = True
            response = self.render(request, self.prepare(request, instance))
        else:
            data = {
                'message': 'Cannot update query',
                'errors': dict(form.errors),
            }
            response = self.render(request, data,
                                   status=codes.unprocessable_entity)
        return response

    def delete(self, request, **kwargs):
        instance = self.get_object(request, **kwargs)

        if instance.session:
            data = {
                'message': 'Cannot delete session query',
            }
            return self.render(request, data, status=codes.bad_request)

        send_mail(instance.shared_users.values_list('email', flat=True),
                  DELETE_QUERY_EMAIL_TITLE.format(instance.name),
                  DELETE_QUERY_EMAIL_BODY.format(instance.name))

        instance.delete()
        usage.log('delete', instance=instance, request=request)
        request.session.modified = True


def prune_context(cxt):
    if 'children' in cxt:
        cxt['children'] = map(prune_context, cxt['children'])
    else:
        cxt = {
            'concept': cxt.get('concept'),
            'field': cxt.get('field'),
            'operator': cxt.get('operator'),
            'value': cxt.get('value'),
        }

    return cxt


class QuerySqlResource(QueryBase):
    def is_unauthorized(self, request, *args, **kwargs):
        if super(QuerySqlResource, self)\
                .is_unauthorized(request, *args, **kwargs):
            return True

        return not any((
            request.user.is_superuser,
            request.user.is_staff,
            settings.DEBUG,
        ))

    def is_not_found(self, request, response, **kwargs):
        return self.get_object(request, **kwargs) is None

    def get(self, request, **kwargs):
        params = self.get_params(request)
        instance = self.get_object(request, **kwargs)

        QueryProcessor = pipeline.query_processors[params['processor']]
        processor = QueryProcessor(tree=params['tree'],
                                   context=instance.context,
                                   view=instance.view)
        queryset = processor.get_queryset(request=request)

        sql, params = queryset.query.get_compiler(queryset.db).as_sql()

        return {
            'description': {
                'context': prune_context(instance.context_json),
                'view': instance.view_json,
            },
            'representation': {
                'sql': sql,
                'params': params,
            },
        }
