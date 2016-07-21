import functools
import logging
from datetime import datetime
from django.conf import settings
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from django.views.decorators.cache import never_cache
from restlib2.http import codes
from restlib2.params import Parametizer, StrParam
from preserialize.serialize import serialize
from modeltree.tree import trees, MODELTREE_DEFAULT_ALIAS
from avocado.events import usage
from avocado.models import DataContext
from avocado.query import pipeline
from serrano.forms import ContextForm
from .base import ThrottledResource
from .history import RevisionsResource, ObjectRevisionsResource, \
    ObjectRevisionResource
from ..links import reverse_tmpl
from . import templates

log = logging.getLogger(__name__)


def context_posthook(instance, data, request, tree):
    opts = tree.root_model._meta
    data['object_name'] = opts.verbose_name.format()
    data['object_name_plural'] = opts.verbose_name_plural.format()

    return data


class ContextParametizer(Parametizer):
    tree = StrParam(MODELTREE_DEFAULT_ALIAS, choices=trees)
    processor = StrParam('default', choices=pipeline.query_processors)


class ContextBase(ThrottledResource):
    cache_max_age = 0
    private_cache = True

    model = DataContext
    template = templates.Context

    parametizer = ContextParametizer

    def get_link_templates(self, request):
        uri = request.build_absolute_uri

        return {
            'self': reverse_tmpl(
                uri, 'serrano:contexts:single', {'pk': (int, 'id')}),
            'stats': reverse_tmpl(
                uri, 'serrano:contexts:stats', {'pk': (int, 'id')}),
        }

    def prepare(self, request, instance, tree, template=None):
        if template is None:
            template = self.template

        tree = trees[tree]
        posthook = functools.partial(context_posthook, request=request,
                                     tree=tree)
        return serialize(instance, posthook=posthook, **template)

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

    def get_default(self, request):
        default = self.model.objects.get_default_template()

        if not default:
            log.warning('No default template for context objects')
            return

        form = ContextForm(request, {'json': default.json, 'session': True})

        if form.is_valid():
            instance = form.save()
            return instance

        log.error('Error creating default context', extra=dict(form.errors))


class ContextsResource(ContextBase):
    "Resource of contexts"
    def get_links(self, request):
        uri = request.build_absolute_uri

        return {
            'self': uri(reverse('serrano:contexts:active')),
        }

    def get(self, request):
        params = self.get_params(request)
        queryset = self.get_queryset(request)

        # Only create a default if a session exists
        if request.session.session_key:
            queryset = list(queryset)

            if not len(queryset):
                default = self.get_default(request)
                if default:
                    queryset.append(default)

        return self.prepare(request, queryset, tree=params['tree'])

    def post(self, request):
        params = self.get_params(request)
        form = ContextForm(request, request.data)

        if form.is_valid():
            instance = form.save()
            usage.log('create', instance=instance, request=request)

            request.session.modified = True

            data = self.prepare(request, instance, tree=params['tree'])
            return self.render(request, data, status=codes.created)

        data = {
            'message': 'Error creating context',
            'errors': dict(form.errors),
        }

        response = self.render(request, data,
                               status=codes.unprocessable_entity)
        return response


class ContextResource(ContextBase):
    "Resource for accessing a single context"
    def is_not_found(self, request, response, **kwargs):
        return self.get_object(request, **kwargs) is None

    def get(self, request, **kwargs):
        params = self.get_params(request)
        instance = self.get_object(request, **kwargs)
        usage.log('read', instance=instance, request=request)

        instance.accessed = datetime.now()
        instance.save(update_fields=('accessed',))

        return self.prepare(request, instance, tree=params['tree'])

    def put(self, request, **kwargs):
        params = self.get_params(request)
        instance = self.get_object(request, **kwargs)

        form = ContextForm(request, request.data, instance=instance)

        if form.is_valid():
            instance = form.save()
            usage.log('update', instance=instance, request=request)

            request.session.modified = True

            data = self.prepare(request, instance, tree=params['tree'])
            return self.render(request, data)

        data = {
            'message': 'Error updating context',
            'errors': dict(form.errors),
        }
        response = self.render(request, data,
                               status=codes.unprocessable_entity)
        return response

    def delete(self, request, **kwargs):
        instance = self.get_object(request, **kwargs)

        # Cannot delete the current session
        if instance.session:
            data = {
                'message': 'Cannot delete session context',
            }
            return self.render(request, data, status=codes.bad_request)

        instance.delete()
        usage.log('delete', instance=instance, request=request)
        request.session.modified = True


class ContextStatsResource(ContextBase):
    def is_not_found(self, request, response, **kwargs):
        return self.get_object(request, **kwargs) is None

    def get(self, request, **kwargs):
        params = self.get_params(request)
        instance = self.get_object(request, **kwargs)

        QueryProcessor = pipeline.query_processors[params['processor']]
        processor = QueryProcessor(tree=params['tree'])
        queryset = processor.get_queryset(request=request)

        return {
            'count': instance.count(queryset=queryset)
        }


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


class ContextSqlResource(ContextBase):
    def is_unauthorized(self, request, *args, **kwargs):
        if super(ContextSqlResource, self)\
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
        processor = QueryProcessor(tree=params['tree'], context=instance)
        queryset = processor.get_queryset(request=request).values('pk')

        sql, params = queryset.query.get_compiler(queryset.db).as_sql()

        return {
            'description': prune_context(instance.json),
            'representation': {
                'sql': sql,
                'params': params,
            },
        }


single_resource = never_cache(ContextResource())
stats_resource = never_cache(ContextStatsResource())
sql_resource = never_cache(ContextSqlResource())
active_resource = never_cache(ContextsResource())
revisions_resource = never_cache(RevisionsResource(
    object_model=DataContext, object_model_template=templates.Context,
    object_model_base_uri='serrano:contexts'))
revisions_for_object_resource = never_cache(ObjectRevisionsResource(
    object_model=DataContext, object_model_template=templates.Context,
    object_model_base_uri='serrano:contexts'))
revision_for_object_resource = never_cache(ObjectRevisionResource(
    object_model=DataContext, object_model_template=templates.Context,
    object_model_base_uri='serrano:contexts'))

# Resource endpoints
urlpatterns = patterns(
    '',
    url(r'^$', active_resource, name='active'),

    # Endpoints for specific contexts
    url(r'^(?P<pk>\d+)/$', single_resource, name='single'),
    url(r'^session/$', single_resource, {'session': True}, name='session'),

    # Stats for a single context
    url(r'^(?P<pk>\d+)/stats/$', stats_resource, name='stats'),
    url(r'^session/stats/$', stats_resource, {'session': True}, name='stats'),

    # SQL for a single context
    url(r'^(?P<pk>\d+)/sql/$', sql_resource, name='sql'),
    url(r'^session/sql/$', sql_resource, {'session': True}, name='sql'),

    # Revision related endpoints
    url(r'^revisions/$', revisions_resource, name='revisions'),
    url(r'^(?P<pk>\d+)/revisions/$', revisions_for_object_resource,
        name='revisions_for_object'),
    url(r'^(?P<object_pk>\d+)/revisions/(?P<revision_pk>\d+)/$',
        revision_for_object_resource, name='revision_for_object'),
)
