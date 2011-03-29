from django.conf.urls.defaults import * #@UnusedWildImport
from django.conf import settings
from piston.resource import Resource
from django.contrib import admin
from django.views.generic.simple import direct_to_template
from webservice_tools import urls as ws_urls
from webservice_tools.views import newResetPass
from mainapp.handlers import * #@UnusedWildImport


# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^templateproject/', include('templateproject.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)
