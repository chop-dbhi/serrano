from itertools import groupby

from django.http import HttpResponse
from django.core.urlresolvers import reverse
from restlib import http
from restlib.http import resources
from avocado.conf import settings
from avocado.fields import logictree
from serrano.utils import uni2str

class CategoryResource(resources.ModelResource):
    "Resource for ``avocado.Category``"

    model = 'avocado.Category'

    def GET(self, request):
        categories = self.queryset(request).values('id', 'name')
        return list(categories)


class CriterionResource(resources.ModelResource):
    model = 'avocado.Criterion'

    def queryset(self, request):
        "Overriden to allow for user specificity."
        # restrict_by_group only in effect when FIELD_GROUP_PERMISSIONS is
        # enabled
        if settings.FIELD_GROUP_PERMISSIONS:
            groups = request.user.groups.all()
            return self.model.objects.restrict_by_group(groups)
        return self.model.objects.public()

    def GET(self, request, pk=None, *args, **kwargs):
        queryset = self.queryset(request)

        if pk is not None:
            try:
                obj = queryset.get(pk=pk)
            except self.model.DoesNotExist:
                return HttpResponse(status=http.NOT_FOUND)
            return obj.view_responses()

        # apply fulltext if the 'q' GET param exists
        if request.GET.has_key('q'):
            queryset = self.model.objects.fulltext_search(request.GET.get('q'),
                queryset, True)
            queryset.query.clear_ordering(True)
            return list(queryset.values_list('id', flat=True))

        queryset = list(queryset.order_by('category', 'order'))

        return [{
            'id': x.id,
            'name': x.name,
            'description': x.description,
            'uri': reverse('api:criteria:read', args=(x.id,))
        } for x in queryset]

    # TODO move this to the ``Scope`` resource since the request is the same --
    # it is merely the response that is different
    def POST(self, request):
        json = uni2str(request.data.copy())

        if not any([x in json for x in ('type', 'operator')]):
            return HttpResponse('Invalid data format', status=http.BAD_REQUEST)

        text = logictree.transform(json).text

        j = ''
        if text.has_key('type'):
            j = ' %s ' % text['type']

        return j.join(text['conditions'])


class ColumnResource(resources.ModelResource):
    model = 'avocado.Column'

    def queryset(self, request):
        "Overriden to allow for user specificity."
        if settings.FIELD_GROUP_PERMISSIONS:
            groups = request.user.groups.all()
            return self.model.objects.restrict_by_group(groups)
        return self.model.objects.public()

    def GET(self, request, *args, **kwargs):
        queryset = self.queryset(request)

        # apply fulltext if the 'q' GET param exists
        if request.GET.has_key('q'):
            queryset = self.model.objects.fulltext_search(request.GET.get('q'),
                queryset, True)
            return list(queryset.values_list('id', flat=True))

        queryset = queryset.order_by('category', 'order')

        # TODO change to flattened out list of columns, not grouped by
        # category since this is only relevent for cilantro as a client
        return [{
            'id': category.id,
            'name': category.name,
            'columns': [{
                'id': x.id,
                'name': x.name,
                'description': x.description
            } for x in columns]
        } for category, columns in groupby(list(queryset),
            lambda x: x.category)]



