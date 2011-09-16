from restlib import http, resources

__all__ = ('CriterionResource', 'CriterionResourceCollection')

class SimpleCriterionResource(resources.ModelResource):
    model = 'avocado.Criterion'
    fields = (':pk', 'name', 'full_description->description', 'category->domain')

    @classmethod
    def queryset(self, request):
        "Overriden to allow for user specificity."
        return self.model.objects.public(user=request.user)

    def GET(self, request, pk):
        obj = self.get(request, pk=pk)

        if not obj:
            return http.NOT_FOUND

        return obj


class CriterionResource(SimpleCriterionResource):
    fields = (':pk', 'name', 'full_description->description',
        'category->domain', 'view_responses->viewset')
    default_for_related = False


class CriterionResourceCollection(resources.ModelResourceCollection):
    resource = SimpleCriterionResource

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
