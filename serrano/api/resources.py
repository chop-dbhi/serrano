from django.http import HttpResponse
from django.utils import simplejson
from restlib.http import resources
from avocado.models import Category

class CategoryResource(resources.Resource):

    def GET(self, request, pk):
        categories = Category.objects.values('id', 'name')
        json = simplejson.dumps(categories)
        return HttpResponse(json, mimetype='application/json')
