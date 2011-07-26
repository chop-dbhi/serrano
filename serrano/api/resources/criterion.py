from django.core.urlresolvers import reverse
from restlib import http, resources
from avocado.fields import logictree
from serrano.utils import uni2str

__all__ = ('CriterionResource', 'CriterionResourceCollection')

class CriterionResource(resources.ModelResource):
    model = 'avocado.Criterion'

    fields = (':pk', 'name', 'full_description->description', 'uri',
        'category->domain')

    @classmethod
    def uri(self, obj):
        return reverse('api:criteria:read', args=(obj.id,))

    @classmethod
    def queryset(self, request):
        "Overriden to allow for user specificity."
        return self.model.objects.public(user=request.user)

    def GET(self, request, pk):
        obj = self.get(request, pk=pk)

        if not obj:
            return http.NOT_FOUND

        return obj.view_responses()


class CriterionResourceCollection(resources.ModelResourceCollection):
    resource = CriterionResource

    middleware = ('serrano.api.middleware.CSRFExemption',) + \
        resources.Resource.middleware

    # HACK.. as with the custom middleware above
    csrf_exempt = True

    def GET(self, request):
        queryset = self.queryset(request)

        # apply fulltext if the 'q' GET param exists
        if request.GET.has_key('q'):
            queryset = self.model.objects.fulltext_search(request.GET.get('q'),
                queryset, True)
            queryset.query.clear_ordering(True)
            return list(queryset.values_list('id', flat=True))

        return queryset.order_by('category', 'order')

    # TODO move this to the ``Scope`` resource since the request is the same --
    # it is merely the response that is different
    def POST(self, request):
        json = uni2str(request.data.copy())

        if not any([x in json for x in ('type', 'operator')]):
            return http.BAD_REQUEST, 'Invalid data format'

        text = logictree.transform(json).text

        j = ''
        if text.has_key('type'):
            j = ' %s ' % text['type']

        return j.join(text['conditions'])



