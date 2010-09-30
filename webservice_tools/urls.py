from django.conf.urls.defaults import *
from piston.resource import Resource
from django.contrib import admin
from  django.views.generic.simple import direct_to_template
admin.autodiscover()

from managementor.handlers import *


basepatterns = patterns('',
    (r'users\.(?P<dataFormat>json|xml)', Resource(UserHandler)),
    (r'users/(?P<userID>[\d]+)/answers\.(?P<dataFormat>xml|json)', Resource(AnswerHandler)),
    (r'users/trusted\.(?P<dataFormat>xml|json)', Resource(TrustedUserHandler)),
    (r'users/trusted/(?P<username>)\.(?P<dataFormat>xml|json)', Resource(TrustedUserHandler)),
    (r'questions\.(?P<dataFormat>xml|json)', Resource(QuestionHandler)),
    (r'questions/(?P<questionID>[\d])\.(?P<dataFormat>xml|json)', Resource(QuestionHandler)),
    (r'answers\.(?P<dataFormat>xml|json)', Resource(AnswerHandler)),
    (r'tags\.(?P<dataFormat>xml|json)', Resource(TagHandler)),
    (r'login\.(?P<dataFormat>xml|json)', Resource(LoginHandler)),
    (r'logout\.(?P<dataFormat>xml|json)', Resource(LoginHandler)),
    (r'apiconsole', direct_to_template, {'template': 'apiconsole.html'}),
    (r'admin/', include(admin.site.urls)),
    (r'geo/', 'managementor.views.geoTest'),
    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    
)

urlpatterns = patterns('',
    (r'^/mmserver', include(basepatterns)),
    (r'', include(basepatterns)))
