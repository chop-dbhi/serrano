from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from django.views.decorators.cache import never_cache
from restlib2 import resources


class Root(resources.Resource):
    def get(self, request):
        return {
            'title': 'Serrano Hypermedia API',
            '_links': {
                'self': {
                    'rel': 'self',
                    'hrf': reverse('serrano:root'),
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
                    'href': reverse('serrano:datacontexts'),
                },
                'views': {
                    'rel': 'dataviews',
                    'href': reverse('serrano:dataviews'),
                },
                'data': {
                    'rel': 'data',
                    'href': reverse('serrano:exporter'),
                }
            }
        }


root_resource = never_cache(Root())

urlpatterns = patterns('',
    url(r'^$', root_resource, name='root')
)
