from django.http import HttpResponse
from django.core.urlresolvers import reverse
from restlib2.http import codes
from restlib2.params import StrParam, IntParam, BoolParam
from avocado.events import usage
from ..pagination import PaginatorResource, PaginatorParametizer
from .base import FieldBase


class FieldValuesParametizer(PaginatorParametizer):
    limit = IntParam(10)
    aware = BoolParam(False)
    query = StrParam()
    random = IntParam()


class FieldValues(FieldBase, PaginatorResource):
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
        for value, label in instance.choices():
            results.append({
                'label': label,
                'value': value,
            })
        return results

    def get_search_values(self, request, instance, query):
        """
        Performs a search on the underlying data for a field.

        This method can be overridden to use an alternate search
        implementation.
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
        limit = params['limit']

        # If a query term is supplied, perform the icontains search
        if params['query']:
            usage.log('values', instance=instance, request=request, data={
                'query': params['query'],
            })
            values = self.get_search_values(request, instance, params['query'])
        else:
            values = self.get_all_values(request, instance)

        # No page specified, return everything
        if page is None:
            return values

        paginator = self.get_paginator(values, limit=limit)
        page = paginator.page(page)

        path = reverse('serrano:field-values', kwargs={'pk': pk})
        links = self.get_page_links(request, path, page, extra=params)

        return {
            'values': page.object_list,
            'limit': paginator.per_page,
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
        except (KeyError, TypeError):
            return HttpResponse('Error parsing value',
                                status=codes.unprocessable_entity)

        field_name = instance.field_name

        # Note, this return a context-aware or naive queryset depending
        # on params
        queryset = self.get_base_values(request, instance, params)
        lookup = {'{0}__in'.format(field_name): values}

        results = set(queryset.filter(**lookup)
                      .values_list(field_name, flat=True))

        for datum in array:
            datum['label'] = instance.get_label(datum['value'])
            datum['valid'] = datum['value'] in results

        usage.log('validate', instance=instance, request=request, data={
            'count': len(array),
        })

        # Return the augmented data
        return request.data
