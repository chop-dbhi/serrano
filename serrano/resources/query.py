import functools
import logging
from datetime import datetime
from django.http import HttpResponse
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.views.decorators.cache import never_cache
from restlib2.http import codes
from preserialize.serialize import serialize
from avocado.models import DataQuery
from avocado.events import usage
from serrano import utils
from serrano.forms import QueryForm
from .base import ThrottledResource
from .history import RevisionsResource, ObjectRevisionsResource, \
    ObjectRevisionResource
from . import templates

log = logging.getLogger(__name__)

DELETE_QUERY_EMAIL_TITLE = "'{0}' has been deleted"
DELETE_QUERY_EMAIL_BODY = """The query named '{0}' has been deleted. You are
 being notified because this query was shared with you. This query is no
 longer available."""


def query_posthook(instance, data, request):
    uri = request.build_absolute_uri
    data['_links'] = {
        'self': {
            'href': uri(reverse('serrano:queries:single', args=[instance.pk])),
        }
    }

    data['is_owner'] = instance.user == request.user

    # If this user is not the owner then the shared users are not included
    # because this sort of data should not be exposed to anyone who isn't the
    # owner of the original query.
    if not data['is_owner']:
        del data['shared_users']

    return data


class QueryBase(ThrottledResource):
    cache_max_age = 0
    private_cache = True

    model = DataQuery
    template = templates.Query

    def prepare(self, request, instance, template=None):
        if template is None:
            template = self.template
        posthook = functools.partial(query_posthook, request=request)
        return serialize(instance, posthook=posthook, **template)

    def get_queryset(self, request, **kwargs):
        "Constructs a QuerySet for this user or session."

        if hasattr(request, 'user') and request.user.is_authenticated():
            kwargs['user'] = request.user
        elif request.session.session_key:
            kwargs['session_key'] = request.session.session_key
        else:
            # The only case where kwargs is empty is for non-authenticated
            # cookieless agents.. e.g. bots, most non-browser clients since
            # no session exists yet for the agent.
            return self.model.objects.none()

        return self.model.objects.filter(**kwargs)


class QueriesResource(QueryBase):
    "Resource for accessing the queries a shared with or owned by a user"
    template = templates.Query

    def prepare(self, request, instance, template=None):
        if template is None:
            template = self.template
        posthook = functools.partial(query_posthook, request=request)
        return serialize(instance, posthook=posthook, **template)

    def get_queryset(self, request, **kwargs):
        if hasattr(request, 'user') and request.user.is_authenticated():
            f = Q(user=request.user) | Q(shared_users__pk=request.user.pk)
            return self.model.objects.filter(**kwargs).filter(f) \
                .order_by('-accessed').distinct()
        else:
            return super(QueriesResource, self).get_queryset(request, **kwargs)

    def get(self, request):
        queryset = self.get_queryset(request)
        return self.prepare(request, queryset)

    def post(self, request):
        form = QueryForm(request, request.data)

        if form.is_valid():
            instance = form.save()
            usage.log('create', instance=instance, request=request)
            response = self.render(request, self.prepare(request, instance),
                                   status=codes.created)
        else:
            response = self.render(request, dict(form.errors),
                                   status=codes.unprocessable_entity)
        return response


class QueryResource(QueryBase):
    "Resource for accessing a single query"
    def get_object(self, request, pk=None, session=None, **kwargs):
        if not pk and not session:
            raise ValueError('A pk or session must used for the lookup')

        queryset = self.get_queryset(request, **kwargs)

        try:
            if pk:
                return queryset.get(pk=pk)
            else:
                return queryset.get(session=True)
        except self.model.DoesNotExist:
            pass

    def is_not_found(self, request, response, **kwargs):
        instance = self.get_object(request, **kwargs)
        if instance is None:
            return True
        request.instance = instance

    def get(self, request, **kwargs):
        usage.log('read', instance=request.instance, request=request)
        self.model.objects.filter(pk=request.instance.pk).update(
            accessed=datetime.now())
        return self.prepare(request, request.instance)

    def put(self, request, **kwargs):
        instance = request.instance
        form = QueryForm(request, request.data, instance=instance)

        if form.is_valid():
            instance = form.save()
            usage.log('update', instance=instance, request=request)
            response = self.render(request, self.prepare(request, instance))
        else:
            response = self.render(request, dict(form.errors),
                                   status=codes.unprocessable_entity)
        return response

    def delete(self, request, **kwargs):
        if request.instance.session:
            return HttpResponse(status=codes.bad_request)

        utils.send_mail(
            request.instance.shared_users.values_list('email', flat=True),
            DELETE_QUERY_EMAIL_TITLE.format(request.instance.name),
            DELETE_QUERY_EMAIL_BODY.format(request.instance.name))

        request.instance.delete()
        usage.log('delete', instance=request.instance, request=request)
        return HttpResponse(status=codes.no_content)


single_resource = never_cache(QueryResource())
active_resource = never_cache(QueriesResource())
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
    url(r'^(?P<pk>\d+)/$', single_resource, name='single'),
    url(r'^session/$', single_resource, {'session': True}, name='session'),

    # Revision related endpoints
    url(r'^revisions/$', revisions_resource, name='revisions'),
    url(r'^(?P<pk>\d+)/revisions/$', revisions_for_object_resource,
        name='revisions_for_object'),
    url(r'^(?P<object_pk>\d+)/revisions/(?P<revision_pk>\d+)/$',
        revision_for_object_resource, name='revision_for_object'),
)
