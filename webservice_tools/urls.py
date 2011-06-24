from django.conf.urls.defaults import *
from webservice_tools.utils import Resource
from webservice_tools.views import *
from django.conf import settings
urlpatterns = patterns('webservice_tools.views',
    (r'geo$', Resource(GeoHandler)),
    (r'resetpass/?$', Resource(ResetPassHandler)),
    (r'locations/?$', Resource(PlacesHandler)),
    (r'amialive/?$', Resource(KeepAliveHandler)),
    (r'docs/?$', Resource(DocHandler)),
    (r'^apiconsole/?$', direct_to_template, {'template': 'apiconsole.html', 'extra_context': {'baseURL': '/%s/' % settings.SERVER_NAME}}),
    
    )
