import logging
from datetime import datetime
from django.conf import settings
from django.conf.urls import patterns, url
from django.views.decorators.cache import never_cache
from restlib2.http import codes
from restlib2.params import Parametizer, StrParam
from preserialize.serialize import serialize
from modeltree.tree import trees, MODELTREE_DEFAULT_ALIAS
from avocado.models import DataView
from avocado.events import usage
from avocado.query import pipeline
from serrano.forms import ViewForm
from .base import ThrottledResource
from .history import RevisionsResource, ObjectRevisionsResource, \
    ObjectRevisionResource
from . import templates
from ..links import reverse_tmpl

log = logging.getLogger(__name__)


class ViewParametizer(Parametizer):
    tree = StrParam(MODELTREE_DEFAULT_ALIAS, choices=trees)
    processor = StrParam('default', choices=pipeline.query_processors)


class ViewBase(ThrottledResource):
    cache_max_age = 0
    private_cache = True

    model = DataView
    template = templates.View

    parametizer = ViewParametizer

    def get_link_templates(self, request):
        uri = request.build_absolute_uri

        return {
            'self': reverse_tmpl(
                uri, 'serrano:views:single', {'pk': (int, 'id')})
        }

    def prepare(self, request, instance, template=None):
        if template is None:
            template = self.template

        return serialize(instance, **template)

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
            log.warning('No default template for view objects')
            return

        form = ViewForm(request, {'json': default.json, 'session': True})

        if form.is_valid():
            instance = form.save()
            return instance

        log.error('Error creating default view', extra=dict(form.errors))


class ViewsResource(ViewBase):
    "Resource of views"
    def get(self, request):
        queryset = self.get_queryset(request)

        # Only create a default is a session exists
        if request.session.session_key:
            queryset = list(queryset)

            if not len(queryset):
                default = self.get_default(request)
                if default:
                    queryset.append(default)

        return self.prepare(request, queryset)

    def post(self, request):
        form = ViewForm(request, request.data)

        if form.is_valid():
            instance = form.save()
            usage.log('create', instance=instance, request=request)
            request.session.modified = True
            response = self.render(request, self.prepare(request, instance),
                                   status=codes.created)
        else:
            data = {
                'message': 'Cannot create view',
                'errors': dict(form.errors),
            }
            response = self.render(request, data,
                                   status=codes.unprocessable_entity)
        return response


class ViewResource(ViewBase):
    "Resource for accessing a single view"
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

        form = ViewForm(request, request.data, instance=instance)

        if form.is_valid():
            instance = form.save()
            usage.log('update', instance=instance, request=request)
            request.session.modified = True
            response = self.render(request, self.prepare(request, instance))
        else:
            data = {
                'message': 'Cannot update view',
                'errors': dict(form.errors),
            }
            response = self.render(request, data,
                                   status=codes.unprocessable_entity)
        return response

    def delete(self, request, **kwargs):
        instance = self.get_object(request, **kwargs)

        if instance.session:
            data = {
                'message': 'Cannot delete session view',
            }
            return self.render(request, data, status=codes.bad_request)

        instance.delete()
        usage.log('delete', instance=instance, request=request)
        request.session.modified = True


class ViewSqlResource(ViewBase):
    def is_unauthorized(self, request, *args, **kwargs):
        if super(ViewSqlResource, self)\
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
        processor = QueryProcessor(tree=params['tree'], view=instance)
        queryset = processor.get_queryset(request=request)

        sql, params = queryset.query.get_compiler(queryset.db).as_sql()

        return {
            'description': instance.json,
            'representation': {
                'sql': sql,
                'params': params,
            },
        }

single_resource = never_cache(ViewResource())
active_resource = never_cache(ViewsResource())
sql_resource = never_cache(ViewSqlResource)
revisions_resource = never_cache(RevisionsResource(
    object_model=DataView, object_model_template=templates.View,
    object_model_base_uri='serrano:views'))
revisions_for_object_resource = never_cache(ObjectRevisionsResource(
    object_model=DataView, object_model_template=templates.View,
    object_model_base_uri='serrano:views'))
revision_for_object_resource = never_cache(ObjectRevisionResource(
    object_model=DataView, object_model_template=templates.View,
    object_model_base_uri='serrano:views'))

# Resource endpoints
urlpatterns = patterns(
    '',
    url(r'^$', active_resource, name='active'),

    # Endpoints for specific views
    url(r'^(?P<pk>\d+)/$', single_resource, name='single'),
    url(r'^session/$', single_resource, {'session': True}, name='session'),

    # Endpoints for specific views
    url(r'^(?P<pk>\d+)/sql/$', sql_resource, name='sql'),
    url(r'^session/sql/$', sql_resource, {'session': True}, name='sql'),

    # Revision related endpoints
    url(r'^revisions/$', revisions_resource, name='revisions'),
    url(r'^(?P<pk>\d+)/revisions/$', revisions_for_object_resource,
        name='revisions_for_object'),
    url(r'^(?P<object_pk>\d+)/revisions/(?P<revision_pk>\d+)/$',
        revision_for_object_resource, name='revision_for_object'),
)
