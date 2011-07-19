import datetime
from django.db import models
from django.conf import settings
import sys
from django.db.models.base import ModelBase

class FriendRequest(models.Model):
    request_from = models.ForeignKey(settings.AUTH_PROFILE_MODULE)
    request_to = models.ForeignKey(settings.AUTH_PROFILE_MODULE, related_name='currentfriendrequests')
    message = models.CharField(max_length='512', default='')
    when_created = models.DateTimeField(default=datetime.datetime.utcnow)
    
    
class FriendGroup(models.Model):
    name = models.CharField(max_length=64)
    owner = models.ForeignKey(settings.AUTH_PROFILE_MODULE, related_name='groups')
    members = models.ManyToManyField(settings.AUTH_PROFILE_MODULE, related_name="member_of", null=True)
    
    def __unicode__(self):
        return self.name
    
    def dict(self):
        ret = {"id": self.id,
               "name":self.name,
               "members": [member.dict() for member in self.members.all()]}
        return ret
    
    
#ALL DEFINITION EOF
module_name = globals().get('__name__')
models = sys.modules[module_name]
models._all_ = []
for model_name in dir():
    m = getattr(models, model_name)
    if isinstance(m, ModelBase) and not m._meta.abstract:
        models._all_.append(model_name)