from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
import sys
from django.db.models.base import ModelBase

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

#ALL DEFINITION EOF
module_name = globals().get('__name__')
models = sys.modules[module_name]
models._all_ = []
for model_name in dir():
    m = getattr(models, model_name)
    if isinstance(m, ModelBase) and not m._meta.abstract:
        models._all_.append(model_name)