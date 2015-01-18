import logging
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.utils.encoding import smart_unicode
from restlib2.http import codes
from restlib2.params import StrParam, IntParam, BoolParam
from modeltree.tree import MODELTREE_DEFAULT_ALIAS, trees
from avocado.events import usage
from avocado.query import pipeline
from .base import FieldBase, is_field_orphaned
from ..pagination import PaginatorResource, PaginatorParametizer
from ...links import patch_response, reverse_tmpl


log = logging.getLogger(__name__)


class FieldValuesParametizer(PaginatorParametizer):
    aware = BoolParam(False)
    limit = IntParam(10)
    tree = StrParam(MODELTREE_DEFAULT_ALIAS, choices=trees)
    processor = StrParam('default', choices=pipeline.query_processors)
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

    def get_all_values(self, request, instance, queryset):
        "Returns all distinct values for this field."
        results = []
        for value, label in instance.choices(queryset=queryset):
            results.append({
                'label': label,
                'value': value,
            })
        return results

    def get_search_values(self, request, instance, query, queryset):
        """
        Performs a search on the underlying data for a field.

        This method can be overridden to use an alternate search
        implementation.
        """
        results = []
        value_labels = instance.value_labels(queryset=queryset)

        for value in instance.search(query, queryset=queryset):
            results.append({
                'label': value_labels.get(value, smart_unicode(value)),
                'value': value,
            })
        return results

    def get_random_values(self, request, instance, random, queryset):
        """
        Returns a random set of value/label pairs.

        This is useful for pre-populating documents or form fields with
        example data.
        """
        values = instance.random(random, queryset=queryset)
        results = []

        for value in values:
            results.append({
                'label': instance.get_label(value, queryset=queryset),
                'value': value,
            })

        return results

    def get_link_templates(self, request):
        uri = request.build_absolute_uri

        return {
            'parent': reverse_tmpl(
                uri, 'serrano:field', {'pk': (int, 'parent_id')})
        }

    def get(self, request, pk):
        instance = self.get_object(request, pk=pk)

        if is_field_orphaned(instance):
            data = {
                'message': 'Orphaned fields do not support values calls.'
            }
            return self.render(
                request, data, status=codes.unprocessable_entity)

        params = self.get_params(request)

        if params['aware']:
            context = self.get_context(request)
        else:
            context = None

        QueryProcessor = pipeline.query_processors[params['processor']]
        processor = QueryProcessor(tree=instance.model, context=context)
        queryset = processor.get_queryset(request=request)

        if params['random']:
            # In the case that the queryset contains a population smaller than
            # the number of random items being requested, a ValueError will be
            # triggered. Instead of passing the error on to the client, we
            # simply return all the possible values.
            try:
                return self.get_random_values(
                    request, instance, params['random'], queryset)
            except ValueError:
                return instance.values(queryset=queryset)

        page = params['page']
        limit = params['limit']

        # If a query term is supplied, perform the icontains search.
        if params['query']:
            usage.log('items', instance=instance, request=request, data={
                'query': params['query'],
            })
            values = self.get_search_values(
                request, instance, params['query'], queryset)
        else:
            values = self.get_all_values(request, instance, queryset)

        # No page specified, return everything.
        if page is None:
            return values

        paginator = self.get_paginator(values, limit=limit)
        page = paginator.page(page)

        # Get paginator-based response.
        data = self.get_page_response(request, paginator, page)

        data.update({
            'items': page.object_list,
        })

        # Add links.
        path = reverse('serrano:field-values', kwargs={'pk': pk})
        links = self.get_page_links(request, path, page, extra=params)
        templates = self.get_link_templates(request)
        response = self.render(request, content=data)

        return patch_response(request, response, links, templates)

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
            # Value takes precedence over label if supplied.
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

        # Validate based on the label.
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

        # Return the augmented data.
        return request.data
