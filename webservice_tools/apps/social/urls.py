from django.conf.urls.defaults import *
from webservice_tools.utils import Resource
from webservice_tools.apps.social.handlers import SocialRegisterHandler, SocialPostHandler
from webservice_tools.apps.social.handlers import SocialFriendHandler, SocialCallbackHandler
urlpatterns = patterns('',
    (r'^register/(?P<network>[\w]+)/?$', Resource(SocialRegisterHandler)),
    (r'^post/?$', Resource(SocialPostHandler)),
    (r'^friends/?$', Resource(SocialFriendHandler)),
    (r'^callback/(?P<network>[\w]+)/?$', Resource(SocialCallbackHandler)),
)
