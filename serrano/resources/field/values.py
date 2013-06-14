from avocado.conf import OPTIONAL_DEPS
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from restlib2.http import codes
from restlib2.params import Parametizer, param_cleaners
from .base import FieldBase


MAXIMUM_RANDOM = 100


class FieldValuesParametizer(Parametizer):
    aware = False
    query = None
    random = None

    page = 1
    per_page = 10

    def clean_aware(self, value):
        return param_cleaners.clean_bool(value)

    def clean_query(self, value):
        return param_cleaners.clean_string(value)

    def clean_random(self, value):
        value = param_cleaners.clean_int(value)
        return min(value, MAXIMUM_RANDOM)

    def clean_per_page(self, value):
        return param_cleaners.clean_int(value)

    def clean_page(self, value):
        return param_cleaners.clean_int(value)


class FieldValues(FieldBase):
    """Field Values Resource

    This resource can be overriden for any field to use a more
    performant search implementation.
    """

    parametizer = FieldValuesParametizer

    def get_base_values(self, request, instance, params):
        "Returns the base queryset for this field."
        # The `aware` flag toggles the behavior of the distribution by making
        # relative to the applied context or none
        if params['aware']:
            context = self.get_context(request)
        else:
            context = self.get_context(request, attrs={})
        return context.apply(queryset=instance.model.objects.all())

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

        if params['random']:
            return self.get_random_values(request, instance, params['random'])

        page = params['page']
        per_page = params['per_page']

        # If a query term is supplied, perform the icontains search
        if params['query']:
            values = self.get_search_values(request, instance, params['query'])
        else:
            values = self.get_all_values(request, instance)

        # No page specified, return everything
        if not page:
            return values

        # Standard pagination components. A buffered paginator is used
        # here which takes a pre-computed count to same a bit of performance.
        # Otherwise the Paginator class itself would execute a count on
        # initialization.
        paginator = Paginator(values, per_page=per_page)

        try:
            page = paginator.page(page)
        except PageNotAnInteger:
            page = paginator.page(1)
        except EmptyPage:
            page = paginator.page(paginator.num_pages)

        uri = request.build_absolute_uri
        path = reverse('serrano:field-values', kwargs={'pk': pk})
        fmtstr = '{0}?page={1}&per_page={2}'

        # Augment previous and next page links if other pages exist
        links = {
            'self': {
                'href': uri(fmtstr.format(path, page.number, per_page)),
            },
            'base': {
                'href': uri(path),
            }
        }

        if page.number != 1:
            links['prev'] = {
                'href': uri(fmtstr.format(path, page.number - 1, per_page)),
            }

        if page.number < paginator.num_pages - 1:
            links['next'] = {
                'href': uri(fmtstr.format(path, page.number + 1, per_page)),
            }

        return {
            'values': page.object_list,
            'per_page': paginator.per_page,
            'num_pages': paginator.num_pages,
            'page_num': page.number,
            '_links': links,
        }

    def post(self, request, pk):
        instance = request.instance
        params = self.get_params(request)

        if isinstance(request.data, dict):
            array = [request.data]
        else:
            array = request.data

        try:
            values = map(lambda x: x['value'], array)
        except (KeyError, TypeError) as e:
            return HttpResponse('Error parsing value',
                status=codes.unprocessable_entity)

        field_name = instance.field_name

        # Note, this return a context-aware or naive queryset depending
        # on params
        queryset = self.get_base_values(request, instance, params)
        lookup = {'{0}__in'.format(field_name): values}

        results = set(queryset.filter(**lookup)\
            .values_list(field_name, flat=True))

        for datum in array:
            datum['label'] = instance.get_label(datum['value'])
            datum['valid'] = datum['value'] in results

        # Return the augmented data
        return request.data
