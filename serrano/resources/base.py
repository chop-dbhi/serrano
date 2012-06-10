from restlib2.resources import Resource
from avocado.models import DataContext


class BaseResource(Resource):
    param_defaults = {}

    def get_params(self, request):
        params = request.GET.copy()
        for param, default in self.param_defaults.items():
            params.setdefault(param, default)
        return params

    def get_context(self, request):
        params = self.get_params(request)
        context = params.get('context')

        # Explicit request to not use a context
        if context != 'null':
            kwargs = {
                'archived': False,
            }
            if hasattr(request, 'user') and request.user.is_authenticated():
                kwargs['user'] = request.user
            else:
                kwargs['session_key'] = request.session.session_key

            # Assume it is a primary key and fallback to the sesssion
            try:
                kwargs['pk'] = int(context)
            except (ValueError, TypeError):
                kwargs['session'] = True

            try:
                return DataContext.objects.get(**kwargs)
            except DataContext.DoesNotExist:
                pass

        return DataContext()
