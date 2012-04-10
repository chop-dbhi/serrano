from restlib2 import resources, utils
from avocado.models import Criterion

class CriterionResource(resources.Resource):
    data_template = {
        'keymap': {'full_description': 'description', 'category': 'domain',
            'view_responses': 'viewset'},
        'fields': [':pk', 'name', 'full_description', 'category',
            'view_responses']
    }

    def is_not_found(self, request, response, pk):
        return not Criterion.objects.public(user=request.user).filter(pk=pk).exists()

    def get(self, request, pk):
        obj = Criterion.objects.public(user=request.user).get(pk=pk)
        return utils.serialize(obj, **self.data_template)

class CriteriaResource(resources.Resource):
    data_template = {
        'keymap': {'full_description': 'description', 'category': 'domain'},
        'fields': [':pk', 'name', 'full_description', 'category'],
    }

    search_template = {
        'fields': [':pk'],
        'values_list': True,
        'flat': True,
    }

    def get(self, request):
        queryset = Criterion.objects.public(user=request.user)

        # Apply fulltext if the 'q' GET param exists
        if request.GET.has_key('q'):
            queryset = Criterion.objects.fulltext_search(request.GET.get('q'), queryset, True)
            queryset.query.clear_ordering(True)
            return utils.serialize(queryset, **self.search_template)

        queryset = queryset.order_by('category', 'order')
        return utils.serialize(queryset, **self.data_template)
