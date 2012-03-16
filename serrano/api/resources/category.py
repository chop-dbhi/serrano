from restlib2 import resources, utils
from avocado.models import Category

class DomainsResource(resources.Resource):
    def get(self, request):
        return utils.serialize(Category.objects.all())
