from django.core.urlresolvers import reverse
from restlib import http, resources

__all__ = ('CategoryResource', 'CategoryResourceCollection',)

class CategoryResource(resources.ModelResource):
    model = 'avocado.Category'

    fields = (':pk', 'name', 'url', 'parent', 'order')

    @classmethod
    def url(self, obj):
        return reverse('api:categories:read', args=(obj.id,))

    def GET(self, request, pk):
        obj = self.get(request, pk=pk)

        if not obj:
            return http.NOT_FOUND

        return obj


class CategoryResourceCollection(resources.ModelResourceCollection):
    resource = CategoryResource

    def GET(self, request):
        return self.queryset(request).all()
