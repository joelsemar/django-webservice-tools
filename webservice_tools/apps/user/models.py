from django.db import models
from webservice_tools import db_utils, encryption
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



class SocialNetwork(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=512)
    display_name = models.CharField(max_length=512)
    base_url = models.CharField(max_length=512)
    request_token_path = models.CharField(max_length=512, null=True)
    access_token_path = models.CharField(max_length=512, null=True)
    auth_path = models.CharField(max_length=512, null=True)
    scope_string = models.CharField(max_length=512, default='publish_stream, offline_access', blank=True)
    api_key = models.CharField(max_length=1028, null=True, help_text='This field is encrypted')
    app_secret = models.CharField(max_length=1028, null=True, help_text='This field is encrypted')
    app_id = models.CharField(max_length=1028, null=True, help_text='This field is encrypted', blank=True)
    
    
    def getRequestTokenURL(self):
        return 'https://%s/%s' % (self.base_url, self.request_token_path)
    
    def getAccessTokenURL(self):
        return 'https://%s/%s' % (self.base_url, self.access_token_path)
    
    def getAuthURL(self):
        return 'https://%s/%s' % (self.base_url, self.auth_path)
    
    def getCallBackURL(self, request):
        if hasattr(settings, 'SOCIAL_PATH'):
            path = settings.SOCIAL_PATH
        else:
            path = '%s/user' % settings.SERVER_NAME
           
        return 'https://%s/%s/%s' % (request.META['HTTP_HOST'], path, self.name)
    
    def getCredentials(self):
        return (self.getKey(), self.getSecret())
    
    def getKey(self):
        return encryption.decryptData(self.api_key)
    
    def getSecret(self):
        return encryption.decryptData(self.app_secret)
    
    def getAppId(self):
        return encryption.decryptData(self.app_id)
    
    def dict(self):
        return {'name': self.name,
                'display_name': self.name,
                'id': self.id}
    
    def __unicode__(self):
        return self.name
        
    class Meta:
        db_table = 'socialnetwork'
        verbose_name = 'Social Network'
        verbose_name_plural = 'Social Networks'
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.api_key = encryption.encryptData(self.api_key)
            self.app_secret = encryption.encryptData(self.app_secret)
            self.app_id = encryption.encryptData(self.app_id)
        else:
            if db_utils.isDirty(self, 'api_key'):
                self.api_key = encryption.encryptData(self.api_key)
        
            if db_utils.isDirty(self, 'app_secret'):
                self.app_secret = encryption.encryptData(self.app_secret)
                
            if db_utils.isDirty(self, 'app_id'):
                self.app_id = encryption.encryptData(self.app_id)
        
        super(SocialNetwork, self).save(*args, **kwargs)



class UserNetworkCredentials(models.Model):
    id = models.AutoField(primary_key=True)
    uuid = models.CharField(max_length=512, db_index=True)
    access_token = models.CharField(max_length=1028)
    profile = models.ForeignKey(settings.AUTH_PROFILE_MODULE)
    network = models.ForeignKey(SocialNetwork)
    post_url = models.CharField(max_length=1028)
    
    class Meta:
        db_table = 'usernetworkcredentials'
        verbose_name = 'User Network Credentials'
        verbose_name_plural = 'User Network Credentials'
         
    def save(self, *args, **kwargs):
        if not self.id or db_utils.isDirty(self, 'access_token'):
            self.access_token = encryption.encryptData(self.access_token)
        
        super(UserNetworkCredentials, self).save(*args, **kwargs)
    
    @property
    def token(self):
        return encryption.decryptData(self.access_token)
