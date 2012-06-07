from django.template import defaultfilters as filters
from avocado.formatters import Formatter, registry


class HTMLFormatter(Formatter):
    def to_html(self, values, fields=None, **context):
        toks = []
        for value in values.values():
            if value is None:
                continue
            if type(value) is float:
                tok = filters.floatformat(value)
            else:
                tok = unicode(value)
            toks.append(tok)
        return u' '.join(toks)

    to_html.process_multiple = True


registry.register(HTMLFormatter, 'HTML')
