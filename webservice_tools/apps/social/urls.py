from django.conf.urls.defaults import *
from webservice_tools.utils import Resource
from webservice_tools.apps.social.handlers import FacebookHandler, TwitterHandler 
urlpatterns = patterns('',
    (r'^(?P<network>facebook)/?$', Resource(FacebookHandler)),
    (r'^(?P<network>twitter)/?$', Resource(TwitterHandler)),
)
