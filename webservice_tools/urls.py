from django.conf.urls.defaults import *

urlpatterns = patterns('webservice_tools.views',
    ('geo$', 'geo'),
    ('locations$', 'yahoo_places'),
    ('amialive', 'amialive'))
