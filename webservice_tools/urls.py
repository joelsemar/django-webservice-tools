from django.conf.urls.defaults import *
from piston.resource import Resource
from webservice_tools.views import *
urlpatterns = patterns('webservice_tools.views',
    ('geo$', Resource(GeoHandler)),
    ('resetpass/?$', Resource(ResetPassHandler)),
    ('locations/?$', Resource(PlacesHandler)),
    ('amialive/?$', 'amialive'))
