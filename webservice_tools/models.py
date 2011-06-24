import simplejson
import datetime
from django.db import models

class StoredHandlerResponse(models.Model):
    handler_id = models.CharField(max_length=128, db_index=True)
    response = models.TextField(default='')
    method = models.CharField(max_length=16)
    
    
class StoredHandlerRequest(models.Model):
    handler_id = models.CharField(max_length=128, db_index=True)
    method = models.CharField(max_length=16)
    path = models.CharField(max_length=512)
    test = models.BooleanField(default=False)
    when_created = models.DateTimeField(default=datetime.datetime.utcnow)
    
    def serialize(self):
        stored_params = [p.dict() for p in self.storedhttpparam_set.all()]
        return simplejson.dumps({'method': self.method, 'path': self.path,
                                 'params': dict((k['name'], k['value']) for k in stored_params)})
    
    
    def save(self, *args, **kwargs):
        super(StoredHandlerRequest, self).save(*args, **kwargs)
        all_requests =  StoredHandlerRequest.objects.filter(handler_id=self.handler_id, method=self.method, test=False)
        if len(all_requests) > 50:
            all_requests[0].delete()
            
    
    class Meta:
        ordering = ('when_created',)
    
class StoredHttpParam(models.Model):
    name = models.CharField(max_length=32)
    value = models.TextField(default='')
    request = models.ForeignKey(StoredHandlerRequest)
    
    def dict(self):
        return {'name': self.name, 'value':self.value}
    
