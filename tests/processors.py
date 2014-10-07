from avocado.query.pipeline import QueryProcessor
from avocado.models import DataContext


class FirstTwoByIdQueryProcessor(QueryProcessor):
    def get_queryset(self, queryset=None, **kwargs):
        queryset = super(FirstTwoByIdQueryProcessor, self)\
            .get_queryset(queryset, **kwargs)

        return queryset.filter(id__lt=3)


class FirstTitleQueryProcessor(QueryProcessor):
    def get_queryset(self, queryset=None, **kwargs):
        queryset = super(FirstTitleQueryProcessor, self)\
            .get_queryset(queryset, **kwargs)

        return queryset.filter(id__lt=2)


class UnderTwentyThousandQueryProcessor(QueryProcessor):
    def __init__(self, *args, **kwargs):
        kwargs['context'] = DataContext(json={
            'field': 'tests.title.salary',
            'operator': 'lt',
            'value': 20000,
        })

        super(UnderTwentyThousandQueryProcessor, self)\
            .__init__(*args, **kwargs)


class ManagerQueryProcessor(QueryProcessor):
    def __init__(self, *args, **kwargs):
        kwargs['context'] = DataContext(json={
            'field': 'tests.employee.is_manager',
            'operator': 'exact',
            'value': True,
        })

        super(ManagerQueryProcessor, self).__init__(*args, **kwargs)
