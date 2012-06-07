from avocado.models import DataContext


def get_data_context(pk=None, user=None):
    "Attempt to return the most appropriate DataContext."
    if pk:
        try:
            return DataContext.objects.get(pk=pk, archived=False)
        except DataContext.DoesNotExist:
            pass
    if user and user.is_authenticated():
        try:
            return DataContext.objects.get(user=user, session=True, archived=False)
        except DataContext.DoesNotExist:
            pass
    return DataContext()
