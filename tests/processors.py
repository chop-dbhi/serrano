from avocado.query.pipeline import QueryProcessor
from modeltree.tree import trees
from .models import Employee, Title


class FirstTwoByIdQueryProcessor(QueryProcessor):
    def get_queryset(self, queryset=None, **kwargs):
        if self.context:
            queryset = self.context.apply(queryset=queryset, tree=self.tree)

        if queryset is None:
            queryset = trees[self.tree].get_queryset()

        return queryset.filter(id__lt=3)


class FirstTitleQueryProcessor(QueryProcessor):
    def get_queryset(self, queryset=None, **kwargs):
        return Title.objects.filter(id__lt=2)


class UnderTwentyThousandQueryProcessor(QueryProcessor):
    def get_queryset(self, queryset=None, **kwargs):
        return Title.objects.filter(salary__lt=20000)


class ManagerQueryProcessor(QueryProcessor):
    def get_queryset(self, queryset=None, **kwargs):
        return Employee.objects.filter(is_manager=True)
