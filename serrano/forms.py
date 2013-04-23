from django import forms
from avocado.models import DataContext, DataView


class ContextForm(forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        self.request = request
        super(ContextForm, self).__init__(*args, **kwargs)

    def clean_json(self):
        json = self.cleaned_data.get('json')
        if not self.instance or self.instance.count is None or self.instance.json != json:
            self.count_needs_update = True
        else:
            self.count_needs_update = False
        return json

    def save(self, commit=True, archive=True):
        instance = super(ContextForm, self).save(commit=False)
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
        model = DataContext
        fields = ('name', 'description', 'keywords', 'json', 'session')


class ViewForm(forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        self.request = request
        super(ViewForm, self).__init__(*args, **kwargs)

    def clean_json(self):
        json = self.cleaned_data.get('json')
        if not self.instance or self.instance.count is None or self.instance.json != json:
            self.count_needs_update = True
        else:
            self.count_needs_update = False
        return json

    def save(self, commit=True, archive=True):
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
