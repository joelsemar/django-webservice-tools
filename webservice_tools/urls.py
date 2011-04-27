from django.conf.urls.defaults import *
from piston.resource import Resource
from webservice_tools.views import *
from django.conf import settings
urlpatterns = patterns('webservice_tools.views',
    ('geo$', Resource(GeoHandler)),
    ('resetpass/?$', Resource(ResetPassHandler)),
    ('locations/?$', Resource(PlacesHandler)),
    ('amialive/?$', 'amialive'),
    ('docs/?$', Resource(DocHandler)),
    (r'^apiconsole/?$', direct_to_template, {'template': 'apiconsole.html', 'extra_context': {'baseURL': '/%s/' % settings.SERVER_NAME}}),
    (r'^socialtest/?$', direct_to_template, {'template': 'socialtest.html', 'extra_context': {'baseURL': '/%s/' % settings.SERVER_NAME}}),
    (r'^', Resource(DocHandler)),
    )
