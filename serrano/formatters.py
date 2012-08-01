from django.template import defaultfilters as filters
from avocado.formatters import Formatter


class HTMLFormatter(Formatter):
    delimiter = u' '

    html_map = {
        None: '<em>n/a</em>'
    }

    def to_html(self, values, **context):
        toks = []
        for value in values.values():
            # Check the html_map first
            if value in self.html_map:
                tok = self.html_map[value]
            # Ignore NoneTypes
            elif value is None:
                continue
            # Prettify floats
            elif type(value) is float:
                tok = filters.floatformat(value)
            else:
                tok = unicode(value)
            toks.append(tok)
        return self.delimiter.join(toks)

    to_html.process_multiple = True
