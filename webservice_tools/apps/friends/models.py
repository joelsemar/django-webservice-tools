import datetime
from django.db import models
from django.conf import settings

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