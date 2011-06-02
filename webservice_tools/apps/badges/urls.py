from django.conf.urls.defaults import *
from webservice_tools.utils import Resource
from webservice_tools.apps.badges.handlers import BadgeHandler, WonSinceHandler
from django.contrib import admin
admin.autodiscover()  
urlpatterns = patterns('',
    (r'^(?P<id>[\d]+)/?$', Resource(BadgeHandler)),
    (r'^since/?$', Resource(WonSinceHandler)),
)
