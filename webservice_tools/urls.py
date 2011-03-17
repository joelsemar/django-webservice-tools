from django.conf.urls.defaults import *

urlpatterns = patterns('webservice_tools.views', 
    ('geo$','geo'),
    ('amialive', 'amialive'))