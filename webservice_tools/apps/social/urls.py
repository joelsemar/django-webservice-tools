from django.conf.urls.defaults import *
from webservice_tools.utils import Resource
from webservice_tools.apps.social.handlers import SocialRegisterHandler, SocialPostHandler
from webservice_tools.apps.social.handlers import SocialFriendHandler, SocialCallbackHandler
from webservice_tools.views import *
from django.conf import settings
urlpatterns = patterns('',
    (r'^register/(?P<network>[\w]+)/?$', Resource(SocialRegisterHandler)),
    (r'^post/?$', Resource(SocialPostHandler)),
    (r'^friends/?$', Resource(SocialFriendHandler)),
    (r'^callback/(?P<network>[\w]+)/?$', Resource(SocialCallbackHandler)),
    (r'^test/?$', direct_to_template, {'template': 'socialtest.html', 'extra_context': {'baseURL': '/%s/social/register/' % settings.SERVER_NAME}}),
)
