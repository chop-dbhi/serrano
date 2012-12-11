from restlib2.resources import Resource
from avocado.models import DataContext, DataView


class BaseResource(Resource):
    param_defaults = {}

    def get_params(self, request):
        params = request.GET.copy()
        for param, default in self.param_defaults.items():
            params.setdefault(param, default)
        return params

    def get_context(self, request, attrs=None):
        """Returns a DataContext object relative based on `attrs`.

        If `attrs` is a dict, a temporary DataContext will be valiated
        and created. Otherwise it is assumed `attrs` is a primary key
        (or empty) and will return the appropriate DataContext.
        """
        if attrs is None:
            if request.method == 'POST':
                attrs = request.data.get('context')
            elif request.method == 'GET':
                attrs = request.GET.get('context')

        if isinstance(attrs, dict):
            DataContext.validate(attrs)
            return DataContext(json=attrs)

        # Assume a primary key or empty value
        kwargs = {
            'archived': False,
        }

        if hasattr(request, 'user') and request.user.is_authenticated():
            kwargs['user'] = request.user
        else:
            if request.session.session_key is None:
                return DataContext()
            kwargs['session_key'] = request.session.session_key

        # Assume it is a primary key and fallback to the sesssion
        try:
            kwargs['pk'] = int(attrs)
        except (ValueError, TypeError):
            kwargs['session'] = True

        try:
            return DataContext.objects.get(**kwargs)
        except DataContext.DoesNotExist:
            pass

        return DataContext()

    def get_view(self, request, attrs=None):
        """Returns a DataView object relative based on `attrs`.

        If `attrs` is a dict, a temporary DataView will be valiated
        and created. Otherwise it is assumed `attrs` is a primary key
        (or empty) and will return the appropriate DataView.
        """
        if attrs is None:
            if request.method == 'POST':
                attrs = request.data.get('view')
            elif request.method == 'GET':
                attrs = request.GET.get('view')

        if isinstance(attrs, dict):
            DataView.validate(attrs)
            return DataView(json=attrs)

        # Assume a primary key or empty valu
        kwargs = {
            'archived': False,
        }

        if hasattr(request, 'user') and request.user.is_authenticated():
            kwargs['user'] = request.user
        else:
            if request.session.session_key is None:
                return DataView()
            kwargs['session_key'] = request.session.session_key

        # Assume it is a primary key and fallback to the sesssion
        try:
            kwargs['pk'] = int(attrs)
        except (ValueError, TypeError):
            kwargs['session'] = True

        try:
            return DataView.objects.get(**kwargs)
        except DataView.DoesNotExist:
            pass

        return DataView()
