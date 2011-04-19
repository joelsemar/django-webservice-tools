from django.db import models
from django.conf import settings
from django.contrib.auth.models import User

class BaseProfile(models.Model):
    user = models.ForeignKey(User)
    if 'webservice_tools.apps.friends' in settings.INSTALLED_APPS:
        friends = models.ManyToManyField('self')
        
    def __unicode__(self):
        return self.user.username
    
    
    class Meta:
        abstract = True
    
    def create_callback(self):
        pass
    
    def update_callback(self):
        pass
    
    def dict(self):
        return {'username': self.user.username}


