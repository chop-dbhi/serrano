from django import forms
from avocado.models import DataContext, DataView, DataQuery


class ContextForm(forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        self.request = request
        self.count_needs_update = kwargs.pop('force_count', None)
        super(ContextForm, self).__init__(*args, **kwargs)

    def clean_json(self):
        json = self.cleaned_data.get('json')

        if self.count_needs_update is None and self.instance:
            existing = self.instance.json
            if existing or json and existing != json or json and self.instance.count is None:
                self.count_needs_update = True
            else:
                self.count_needs_update = False
        return json

    def save(self, commit=True, archive=False):
        instance = super(ContextForm, self).save(commit=False)
        request = self.request

        if hasattr(request, 'user') and request.user.is_authenticated():
            instance.user = request.user
        else:
            instance.session_key = request.session.session_key

        # Only recalculated count if conditions exist. This is to
        # prevent re-counting the entire dataset. An alternative
        # solution may be desirable such as pre-computing and
        # caching the count ahead of time.
        if self.count_needs_update:
            instance.count = instance.apply().distinct().count()
            self.count_needs_update = False
        else:
            instance.count = None

        if commit:
            instance.save()
            if archive:
                # Should this be a signal?
                instance.archive()
        return instance

    class Meta(object):
        model = DataContext
        fields = ('name', 'description', 'keywords', 'json', 'session')


class ViewForm(forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        self.request = request
        self.count_needs_update = kwargs.pop('force_count', None)
        super(ViewForm, self).__init__(*args, **kwargs)

    def clean_json(self):
        json = self.cleaned_data.get('json')

        if self.count_needs_update is None:
            existing = self.instance.json
            if existing or json and existing != json or json and self.instance.count is None:
                self.count_needs_update = True
            else:
                self.count_needs_update = False
        return json

    def save(self, commit=True, archive=False):
        instance = super(ViewForm, self).save(commit=False)
        request = self.request

        if hasattr(request, 'user') and request.user.is_authenticated():
            instance.user = request.user
        else:
            instance.session_key = request.session.session_key

        if commit:
            instance.save()
            if archive:
                # Should this be a signal?
                instance.archive()
        return instance

    class Meta(object):
        model = DataView
        fields = ('name', 'description', 'keywords', 'json', 'session')

class QueryForm(forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        self.request = request
        self.count_needs_update = kwargs.pop('force_count', None)
        super(QueryForm, self).__init__(*args, **kwargs)

    def clean_json(self):
        # XXX: Does this need to be split into context_json and view_json
        # checks here and in the fields in the Meta class?
        json = self.cleaned_data.get('json')

        if self.count_needs_update is None:
            existing = self.instance.json
            if existing or json and existing != json or json and self.instance.count is None:
                self.count_needs_update = True
            else:
                self.count_needs_update = False
        return json

    def save(self, commit=True, archive=False):
        instance = super(QueryForm, self).save(commit=False)
        request = self.request

        if hasattr(request, 'user') and request.user.is_authenticated():
            instance.user = request.user
        else:
            instance.session_key = request.session.session_key

        if commit:
            instance.save()
            if archive:
                # Should this be a signal?
                instance.archive()
        return instance

    class Meta(object):
        model = DataQuery
        fields = ('name', 'description', 'keywords', 'context_json', 
                'view_json', 'session')
