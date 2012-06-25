from avocado.export import JSONExporter, registry


class JSONHTMLExporter(JSONExporter):
    preferred_formats = ('html', 'string')


registry.register(JSONHTMLExporter, 'json+html')
