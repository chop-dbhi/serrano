from avocado.conf import OPTIONAL_DEPS
from restlib2.params import Parametizer, param_cleaners
from .base import FieldBase


MAXIMUM_RANDOM = 100


class FieldValuesParametizer(Parametizer):
    query = None
    random = None

    def clean_query(self, value):
        return param_cleaners.clean_string(value)

    def clean_random(self, value):
        value = param_cleaners.clean_int(value)
        return min(value, MAXIMUM_RANDOM)


class FieldValues(FieldBase):
    """Field Values Resource

    This resource can be overriden for any field to use a more
    performant search implementation.
    """

    parametizer = FieldValuesParametizer

    def get_all_values(self, request, instance):
        "Returns all distinct values for this field."
        results = []
        for value, label in instance.choices:
            results.append({
                'label': label,
                'value': value,
            })
        return results

    def get_search_values(self, request, instance, query):
        """Performs a search on the underlying data for a field.
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

        # If a query term is supplied, perform the icontains search
        # Searches are only enabled if Haystack is installed
        if params['query'] and OPTIONAL_DEPS['haystack']:
            return self.get_search_values(request, instance, params['query'])

        if params['random']:
            return self.get_random_values(request, instance, params['random'])

        return self.get_all_values(request, instance)
