from avocado.conf import OPTIONAL_DEPS
from .base import DataFieldBase


MAXIMUM_RANDOM = 100


class DataFieldValues(DataFieldBase):
    """DataField Values Resource

    This resource can be overriden for any datafield to use a more
    performant search implementation.
    """

    def get_all_values(self, request, instance):
        "Returns all distinct values for this datafield."
        results = []
        for value, label in instance.choices:
            results.append({
                'label': label,
                'value': value,
            })
        return results

    def get_search_values(self, request, instance, query):
        """Performs a search on the underlying data for a datafield.
        This method can be overridden to use an alternate search implementation.
        """
        results = []
        for value in instance.search(query):
            results.append({
                'label': instance.get_label(value),
                'value': value,
            })
        return results

    def get_random_values(self, request, instance, random):
        """Returns a random set of values. This is useful for pre-populating
        documents or form fields with example data.
        """
        queryset = instance.model.objects.only(instance.field_name)\
            .order_by('?')[:random]

        results = []
        for obj in queryset:
            value = getattr(obj, instance.field_name)
            results.append({
                'label': instance.get_label(value),
                'value': value,
            })
        return results

    def get(self, request, pk):
        instance = request.instance

        params = self.get_params(request)

        # Searches are only enabled if Haystack is installed
        if OPTIONAL_DEPS['haystack']:
            query = params.get('query').strip()
        else:
            query = ''

        try:
            random = min(int(params.get('random')), MAXIMUM_RANDOM)
        except (ValueError, TypeError):
            random = False

        results = []

        # If a query term is supplied, perform the icontains search
        if query:
            return self.get_search_values(request, instance, query)
        # get a random set of values
        elif random:
            return self.get_random_values(request, instance, random)
        # ..otherwise use the cached choices
        else:
            return self.get_all_values(request, instance)
        return results
