from django import forms
from django.db.models import get_model
from django.conf.urls import url, patterns
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from objectset import resources
from objectset.models import ObjectSet
from objectset.forms import objectset_form_factory
from serrano.conf import settings
from .base import BaseResource


URL_REVERSE_NAME = 'serrano:sets:{0}'


def configure_object_set(config):
    model_label = config['model']
    app_name, model_name = model_label.split('.', 1)
    model_name = model_name.lower()

    model = get_model(app_name, model_name)

    if not issubclass(model, ObjectSet):
        raise ImproperlyConfigured('Only models that subclass ObjectSet '
                                   'are supported, not {0}'
                                   .format(model_label))

    default_name = unicode(model._meta.verbose_name_plural)
    name = config.get('name', default_name.lower().replace(' ', ''))
    label = config.get('label', default_name.title())

    options = {
        'label': label,
    }

    url_names = {
        'sets': model_name,
        'set': model_name,
        'objects': '{0}-objects'.format(model_name),
    }

    url_reverse_names = {
        'sets': URL_REVERSE_NAME.format(model_name),
        'set': URL_REVERSE_NAME.format(model_name),
        'objects': URL_REVERSE_NAME.format('{0}-objects'.format(model_name)),
    }

    class ObjectSetForm(objectset_form_factory(model)):
        context = forms.Field(required=False)

        def __init__(self, *args, **kwargs):
            super(ObjectSetForm, self).__init__(*args, **kwargs)

        def clean_context(self):
            self._context_applied = False
            # Extract is from the request data. See
            # ``serrano.resources.base.get_request_context`` for parsing
            # details
            context = self.resource.get_context(self.request)

            if context.json:
                return context

        def save(self, commit=True):
            instance = super(ObjectSetForm, self).save(commit=False)
            context = self.cleaned_data.get('context')

            # Set the `context_json` on the instance if new. This is
            # harmless for models that do not have a `context_json` field
            # defined.
            if not instance.pk and context:
                instance.context_json = context.json

            # Prevents reapplying the context to the pending objects
            if not self._context_applied:
                self._context_applied = True
                if context:
                    instance._pending |= context.apply()

            if commit:
                instance.save()
                self.save_m2m()

            return instance

    bases = (resources.BaseSetResource, BaseResource)

    BaseSetResource = type('BaseSetResource', bases, {
        'model': model,
        'form_class': ObjectSetForm,
        'url_names': url_names,
        'url_reverse_names': url_reverse_names,
        'user_support': config.get('user_support'),
        'session_support': config.get('session_support'),
    })

    options['url_reverse_names'] = url_reverse_names
    options['url_patterns'] = resources.get_url_patterns(model, {
        'base': BaseSetResource
    }, prefix=name)

    return options


urlpatterns = patterns('')
object_set_options = []

for config in settings.OBJECT_SETS:
    options = configure_object_set(config)
    object_set_options.append(options)
    urlpatterns += options['url_patterns']


class SetsRootResource(BaseResource):
    object_set_options = tuple(object_set_options)

    def get_links(self, request):
        uri = request.build_absolute_uri

        links = {}
        for options in self.object_set_options:
            reverses = options['url_reverse_names']

            options['label'] = uri(reverse(reverses['sets']))

        return links

    def get(self, request):

        data = []

        for options in self.object_set_options:
            data.append({
                'label': options['label'],
            })

        return data


sets_root_resource = SetsRootResource()

urlpatterns += patterns('', url(r'^$', sets_root_resource, name='root'))
