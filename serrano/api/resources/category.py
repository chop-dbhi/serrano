from restlib.http import resources

__all__ = ('CategoryResource', 'CategoryResourceCollection',)

class CategoryResource(resources.ModelResource):
    model = 'avocado.Category'
    fields = ('id', 'name')

class CategoryResourceCollection(resources.ModelResourceCollection):
    resource = CategoryResource()
