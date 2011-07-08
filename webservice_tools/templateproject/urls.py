from django.conf.urls.defaults import * #@UnusedWildImport
from django.conf import settings
from webservice_tools.utils import Resource
from django.contrib import admin
from django.views.generic.simple import direct_to_template
from webservice_tools import urls as ws_urls
from webservice_tools.views import newResetPass
from mainapp.handlers import * #@UnusedWildImport
from webservice_tools.views import handler404_view
handler404 = handler404_view

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
admin.autodiscover()

basepatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^services?/', include(ws_urls)),    
    (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root':settings.MEDIA_ROOT}),
)

urlpatterns = patterns('',
    (r'^cwserver/', include(basepatterns)),
    (r'', include(basepatterns)),

)