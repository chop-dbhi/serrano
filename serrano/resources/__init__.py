from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from restlib2 import resources


class Root(resources.Resource):
    def get(self, request):
        return {
            'title': 'Serrano Hypermedia API',
            '_links': {
                'self': {
                    'rel': 'self',
                    'href': reverse('serrano:root'),
                },
                'fields': {
                    'rel': 'datafields',
                    'href': reverse('serrano:datafields'),
                },
                'concepts': {
                    'rel': 'dataconcepts',
                    'href': reverse('serrano:dataconcepts'),
                },
                'contexts': {
                    'rel': 'datacontexts',
                    'href': reverse('serrano:contexts:active'),
                },
                'views': {
                    'rel': 'dataviews',
                    'href': reverse('serrano:views:active'),
                },
                'preview': {
                    'rel': 'data',
                    'href': reverse('serrano:data:preview'),
                },
                'exporter': {
                    'rel': 'data',
                    'href': reverse('serrano:data:exporter'),
                }
            }
        }


root_resource = Root()

urlpatterns = patterns('',
    url(r'^$', root_resource, name='root')
)
