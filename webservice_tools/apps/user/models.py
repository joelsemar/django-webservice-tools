from django.db import models
from django.conf import settings
from django.contrib.auth.models import User

User._meta.get_field_by_name('username')[0].max_length = 75

class BaseProfile(models.Model):
    user = models.OneToOneField(User)
    if 'webservice_tools.apps.friends' in settings.INSTALLED_APPS:
        friends = models.ManyToManyField('self', blank=True)
        
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

