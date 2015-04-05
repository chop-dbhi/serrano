from __future__ import unicode_literals

import functools
import logging
from datetime import datetime
from django.conf.urls import patterns, url
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.views.decorators.cache import never_cache
from restlib2.http import codes
from restlib2.params import IntParam, Parametizer, StrParam
from preserialize.serialize import serialize
from modeltree.tree import trees, MODELTREE_DEFAULT_ALIAS
from avocado.events import usage
from avocado.export import JSONExporter
from avocado.models import DataQuery
from avocado.query import pipeline, utils as query_utils
from serrano.utils import send_mail
from serrano.forms import QueryForm
from .base import ThrottledResource
from .history import RevisionsResource, ObjectRevisionsResource, \
    ObjectRevisionResource
from . import templates
from ..links import reverse_tmpl

log = logging.getLogger(__name__)

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


class QueryResultsParametizer(QueryParametizer):
    limit = IntParam(50)


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

    def get_object(self, request, pk=None, session=None, **kwargs):
        if not pk and not session:
            raise ValueError('A pk or session must used for the lookup')

        if not hasattr(request, 'instance'):
            queryset = self.get_queryset(request, **kwargs)

            try:
                if pk:
                    instance = queryset.get(pk=pk)
                else:
                    instance = queryset.get(session=True)
            except self.model.DoesNotExist:
                instance = None

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


class QueryStatsResource(QueryBase):
    def is_not_found(self, request, response, **kwargs):
        return self.get_object(request, **kwargs) is None

    def get(self, request, **kwargs):
        params = self.get_params(request)
        instance = self.get_object(request, **kwargs)

        QueryProcessor = pipeline.query_processors[params['processor']]
        processor = QueryProcessor(tree=params['tree'])
        queryset = processor.get_queryset(request=request)

        return {
            'distinct_count': instance.context.count(queryset=queryset),
            'record_count': instance.count(queryset=queryset)
        }


class QueryResultsResource(QueryBase):
    QUERY_NAME_TEMPLATE = 'query_result:{pk}'

    parametizer = QueryResultsParametizer

    def get_object(self, request, pk=None, session=None, **kwargs):
        if not pk and not session:
            raise ValueError('A pk or session must used for the lookup')

        if not hasattr(request, 'instance'):
            # Don't pass on page or stop_page.
            filters = dict(kwargs)
            filters.pop('page', None)
            filters.pop('stop_page', None)

            queryset = self.get_queryset(request, **filters)

            try:
                if pk:
                    instance = queryset.get(pk=pk)
                else:
                    instance = queryset.get(session=True)
            except self.model.DoesNotExist:
                instance = None

            request.instance = instance

        return request.instance

    def is_not_found(self, request, response, **kwargs):
        return self.get_object(request, **kwargs) is None

    def get(self, request, **kwargs):
        context = request.instance.context
        view = request.instance.view

        params = self.get_params(request)

        limit = params.get('limit')
        tree = params.get('tree')

        page = kwargs.get('page')
        stop_page = kwargs.get('stop_page')

        offset = None

        if page:
            page = int(page)

            # Pages are 1-based.
            if page < 1:
                raise Http404

            # Change to 0-base for calculating offset.
            offset = limit * (page - 1)

            if stop_page:
                stop_page = int(stop_page)

                # Cannot have a lower index stop page than start page.
                if stop_page < page:
                    raise Http404

                # 4...5 means 4 and 5, not everything up to 5 like with
                # list slices, so 4...4 is equivalent to just 4
                if stop_page > page:
                    limit = limit * stop_page
        else:
            # When no page or range is specified, the limit does not apply.
            limit = None

        QueryProcessor = pipeline.query_processors[params['processor']]
        processor = QueryProcessor(context=context, view=view, tree=tree)
        queryset = processor.get_queryset(request=request)

        # Isolate this query to a named connection. This will cancel an
        # outstanding queries of the same name if one is present.
        query_name = self.QUERY_NAME_TEMPLATE.format(pk=request.instance.pk)
        query_utils.cancel_query(query_name)
        queryset = query_utils.isolate_queryset(query_name, queryset)

        exporter = processor.get_exporter(JSONExporter)

        # This is an optimization when concepts are selected for ordering
        # only. There is not guarantee to how many rows are required to get
        # the desired `limit` of rows, so the query is unbounded. If all
        # ordering facets are visible, the limit and offset can be pushed
        # down to the query.
        order_only = lambda f: not f.get('visible', True)
        view_node = view.parse()
        resp = HttpResponse()

        if filter(order_only, view_node.facets):
            iterable = processor.get_iterable(queryset=queryset,
                                              request=request)

            # Write the data to the response
            exporter.write(iterable,
                           resp,
                           request=request,
                           offset=offset,
                           limit=limit)
        else:
            iterable = processor.get_iterable(queryset=queryset,
                                              request=request,
                                              limit=limit,
                                              offset=offset)

            exporter.write(iterable,
                           resp,
                           request=request)

        return resp

    def delete(self, request, **kwargs):
        query_name = self.QUERY_NAME_TEMPLATE.format(pk=request.instance.pk)
        canceled = query_utils.cancel_query(query_name)
        return self.render(request, {'canceled': canceled})


single_resource = never_cache(QueryResource())
active_resource = never_cache(QueriesResource())
public_resource = never_cache(PublicQueriesResource())
forks_resource = never_cache(QueryForksResource())
stats_resource = never_cache(QueryStatsResource())
results_resource = never_cache(QueryResultsResource())

revisions_resource = never_cache(RevisionsResource(
    object_model=DataQuery, object_model_template=templates.Query,
    object_model_base_uri='serrano:queries'))
revisions_for_object_resource = never_cache(ObjectRevisionsResource(
    object_model=DataQuery, object_model_template=templates.Query,
    object_model_base_uri='serrano:queries'))
revision_for_object_resource = never_cache(ObjectRevisionResource(
    object_model=DataQuery, object_model_template=templates.Query,
    object_model_base_uri='serrano:queries'))

# Resource endpoints
urlpatterns = patterns(
    '',
    url(r'^$', active_resource, name='active'),

    # Endpoints for specific queries
    url(r'^public/$', public_resource, name='public'),

    # Single queries
    url(r'^(?P<pk>\d+)/$', single_resource, name='single'),
    url(r'^session/$', single_resource, {'session': True}, name='session'),

    # Endpoint for retrieving results of an existing query.
    url(
        r'^(?P<pk>\d+)/results/$',
        results_resource,
        name='results'
    ),
    url(
        r'^(?P<pk>\d+)/results/(?P<page>\d+)/$',
        results_resource,
        name='results'
    ),
    url(
        r'^(?P<pk>\d+)/results/(?P<page>\d+)\.\.\.(?P<stop_page>\d+)/$',
        results_resource,
        name='results'
    ),

    # Stats
    url(r'^(?P<pk>\d+)/stats/$', stats_resource, name='stats'),
    url(r'^session/stats/$', stats_resource, {'session': True}, name='stats'),

    # Forks
    # TODO add endpoint for session?
    url(r'^(?P<pk>\d+)/forks/$', forks_resource, name='forks'),

    # Revision related endpoints
    url(r'^revisions/$', revisions_resource, name='revisions'),
    url(r'^(?P<pk>\d+)/revisions/$', revisions_for_object_resource,
        name='revisions_for_object'),
    url(r'^(?P<object_pk>\d+)/revisions/(?P<revision_pk>\d+)/$',
        revision_for_object_resource, name='revision_for_object'),
)
