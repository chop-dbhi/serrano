from avocado.models import DataContext


def get_data_context(pk=None, user=None):
    "Attempt to return the most appropriate DataContext."
    if pk:
        try:
            return DataContext.objects.get(pk=pk)
        except DataContext.DoesNotExist:
            pass
    if user:
        try:
            return DataContext.objects.get(user=user, session=True)
        except DataContext.DoesNotExist:
            pass
    return DataContext()
