from django.conf.urls.defaults import *
from django.conf import settings
from  django.views.generic.simple import direct_to_template
from piston.resource import Resource
from webservice_tools.apps.user.handlers import FacebookHandler, GenericUserHandler, LoginHandler, TwitterHandler 
urlpatterns = patterns('',
    (r'^/?$', Resource(GenericUserHandler)),
    (r'^login/?$', Resource(LoginHandler)),
    (r'^logout/?$', Resource(LoginHandler)),
    (r'^(?P<network>facebook)/?$', Resource(FacebookHandler)),
    (r'^(?P<network>twitter)/?$', Resource(TwitterHandler)),
    
)
