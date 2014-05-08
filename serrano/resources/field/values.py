from django.db.models import Q
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_unicode
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
        value_labels = instance.value_labels()

        for value in instance.search(query):
            results.append({
                'label': value_labels.get(value, smart_unicode(value)),
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
        value_labels = instance.value_labels()

        for obj in queryset:
            value = getattr(obj, instance.field_name)
            results.append({
                'label': value_labels.get(value, smart_unicode(value)),
                'value': value,
            })
        return results

    def get(self, request, pk):
        instance = self.get_object(request, pk=pk)
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

        # Get paginator-based response
        resp = self.get_page_response(request, paginator, page)

        # Add links
        path = reverse('serrano:field-values', kwargs={'pk': pk})

        links = self.get_page_links(request, path, page, extra=params)
        links['parent'] = {
            'href': request.build_absolute_uri(reverse('serrano:field',
                                               kwargs={'pk': pk})),
        }
        resp.update({
            '_links': links,
            'values': page.object_list,
        })

        return resp

    def post(self, request, pk):
        instance = self.get_object(request, pk=pk)
        params = self.get_params(request)

        if not request.data:
            data = {
                'message': 'Error parsing data',
            }
            return self.render(request, data,
                               status=codes.unprocessable_entity)

        if isinstance(request.data, dict):
            array = [request.data]
        else:
            array = request.data

        values = []
        labels = []
        array_map = {}

        # Separate out the values and labels for the lookup. Track indexes
        # maintain order of array
        for i, datum in enumerate(array):
            # Value takes precedence over label if supplied
            if 'value' in datum:
                array_map[i] = 'value'
                values.append(datum['value'])
            elif 'label' in datum:
                array_map[i] = 'label'
                labels.append(datum['label'])
            else:
                data = {
                    'message': 'Error parsing value or label'
                }
                return self.render(request, data,
                                   status=codes.unprocessable_entity)

        value_field_name = instance.field_name
        label_field_name = instance.label_field.name

        # Note, this return a context-aware or naive queryset depending
        # on params. Get the value and label fields so they can be filled
        # in below.
        queryset = self.get_base_values(request, instance, params)\
            .values_list(value_field_name, label_field_name)

        lookup = Q()

        # Validate based on the label
        if labels:
            lookup |= Q(**{'{0}__in'.format(label_field_name): labels})

        if values:
            lookup |= Q(**{'{0}__in'.format(value_field_name): values})

        results = queryset.filter(lookup)

        value_labels = dict(results)
        label_values = dict([(v, k) for k, v in value_labels.items()])

        for i, datum in enumerate(array):
            if array_map[i] == 'label':
                valid = datum['label'] in label_values
                if valid:
                    value = label_values[datum['label']]
                else:
                    value = datum['label']

                datum['valid'] = valid
                datum['value'] = value
            else:
                valid = datum['value'] in value_labels
                if valid:
                    label = value_labels[datum['value']]
                else:
                    label = smart_unicode(datum['value'])

                datum['valid'] = valid
                datum['label'] = label

        usage.log('validate', instance=instance, request=request, data={
            'count': len(array),
        })

        # Return the augmented data
        return request.data
