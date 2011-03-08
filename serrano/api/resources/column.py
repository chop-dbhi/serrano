from itertools import groupby

from restlib.http import resources
from avocado.conf import settings

__all__ = ('ColumnResource', 'ColumnResourceCollection')

class ColumnResource(resources.ModelResource):
    model = 'avocado.Column'

    def queryset(self, request):
        "Overriden to allow for user specificity."
        return self.model.objects.public(user=request.user)


class ColumnResourceCollection(resources.ModelResourceCollection):
    resource = ColumnResource()

    def GET(self, request):
        queryset = self.queryset(request)

        # apply fulltext if the 'q' GET param exists
        if request.GET.has_key('q'):
            queryset = self.model.objects.fulltext_search(request.GET.get('q'),
                queryset, True)
            return list(queryset.values_list('id', flat=True))

        queryset = queryset.order_by('category', 'order')

        # TODO change to flattened out list of columns, not grouped by
        # category since this is only relevent for cilantro as a client
        return [{
            'id': category.id,
            'name': category.name,
            'columns': [{
                'id': x.id,
                'name': x.name,
                'description': x.full_description()
            } for x in columns]
        } for category, columns in groupby(list(queryset),
            lambda x: x.category)]

