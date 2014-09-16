from avocado.query.pipeline import QueryProcessor
from .models import Employee, Title


class FirstTitleQueryProcessor(QueryProcessor):
    def get_queryset(self, queryset=None, **kwargs):
        return Title.objects.filter(id__lt=2)


class UnderTwentyThousandQueryProcessor(QueryProcessor):
    def get_queryset(self, queryset=None, **kwargs):
        return Title.objects.filter(salary__lt=20000)


class ManagerQueryProcessor(QueryProcessor):
    def get_queryset(self, queryset=None, **kwargs):
        return Employee.objects.filter(is_manager=True)
