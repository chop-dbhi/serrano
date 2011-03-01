from django.http import HttpResponse
from django.core.urlresolvers import reverse
from restlib import http
from restlib.http import resources
from avocado.conf import settings
from avocado.fields import logictree
from serrano.utils import uni2str

__all__ = ('CriterionResource', 'CriterionResourceCollection')

class CriterionResource(resources.ModelResource):
    model = 'avocado.Criterion'

    def queryset(self, request):
        "Overriden to allow for user specificity."
        return self.model.objects.public(user=request.user)

    def GET(self, request, pk):
        queryset = self.queryset(request)

        try:
            obj = queryset.get(pk=pk)
        except self.model.DoesNotExist:
            return HttpResponse(status=http.NOT_FOUND)
        return obj.view_responses()


class CriterionResourceCollection(resources.ModelResourceCollection):
    resource = CriterionResource()

    def obj_to_dict(self, obj):
        return {
            'id': obj.id,
            'name': obj.name,
            'description': obj.full_description(),
            'uri': reverse('api:criteria:read', args=(obj.id,)),
            'category': {
                'id': obj.category.id,
                'name': obj.category.name,
                'uri': reverse('api:categories:read', args=(obj.category.id,))
            }
        }

    def GET(self, request):
        queryset = self.queryset(request)

        # apply fulltext if the 'q' GET param exists
        if request.GET.has_key('q'):
            queryset = self.model.objects.fulltext_search(request.GET.get('q'),
                queryset, True)
            queryset.query.clear_ordering(True)
            return list(queryset.values_list('id', flat=True))

        queryset = queryset.order_by('category', 'order')
        return map(self.obj_to_dict, queryset)

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



