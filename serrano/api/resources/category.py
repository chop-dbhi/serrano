from django.http import HttpResponse
from django.core.urlresolvers import reverse
from restlib import http
from restlib.http import resources

__all__ = ('CategoryResource', 'CategoryResourceCollection',)

class CategoryResource(resources.ModelResource):
    model = 'avocado.Category'

    def obj_to_dict(self, obj, *args, **kwargs):
        return {
            'id': obj.id,
            'name': obj.name,
            'uri': reverse('api:categories:read', args=(obj.id,))
        }

    def GET(self, request, pk):
        try:
            obj = self.queryset(request).get(pk=pk)
        except self.model.DoesNotExist:
            return HttpResponse(status=http.NOT_FOUND)

        return self.obj_to_dict(obj)

class CategoryResourceCollection(resources.ModelResourceCollection):
    resource = CategoryResource()
