from restlib2 import resources, utils
from avocado.models import Column

class ColumnsResource(resources.Resource):
    data_template = {
        'select_related': ['category'],
        'fields': [':pk', 'name', 'description', 'category'],
        'keymap': {'category': 'domain'},
        'related': {
            'category': {
                'fields': [':pk', 'name', 'order', 'parent'],
                'related': {
                    'parent': {'fields': [':pk']}
                }
            }
        }
    }

    search_template = {
        'fields': [':pk'],
        'values_list': True,
        'flat': True,
    }

    def get(self, request):
        queryset = Column.objects.public(user=request.user)
        # Apply fulltext if the 'q' GET param exists
        if request.GET.has_key('q'):
            queryset = Column.objects.fulltext_search(request.GET.get('q'), queryset, True)
            queryset.query.clear_ordering(True)
            return utils.serialize(queryset, **self.search_template)

        queryset = queryset.order_by('category', 'order')
        return utils.serialize(queryset, **self.data_template)
