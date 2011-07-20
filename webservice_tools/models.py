import simplejson
import datetime
from webservice_tools import consts, utils
from django.contrib.gis.db import models


class StoredHandlerResponse(models.Model):
    handler_id = models.CharField(max_length=128, db_index=True)
    response = models.TextField(default='')
    method = models.CharField(max_length=16)
    
    
class StoredHandlerRequest(models.Model):
    handler_id = models.CharField(max_length=128, db_index=True)
    method = models.CharField(max_length=16)
    path = models.CharField(max_length=512)
    test = models.BooleanField(default=False)
    auth_test = models.BooleanField(default=False)
    create_user_test = models.BooleanField(default=False)
    priority = models.PositiveIntegerField(default=0)
    when_created = models.DateTimeField(default=datetime.datetime.utcnow)
    
    def __unicode__(self):
        return "%s %s" % (self.method, self.path)
    
    def serialize(self, stored_params):
        ret = {'method': self.method, 'path': self.path, 'priority': self.priority,
               'params': dict((k['name'], k['value']) for k in stored_params)}
        if self.auth_test:
            ret['auth_test'] = self.auth_test
        if self.create_user_test:
            ret['create_user_test'] =  self.create_user_test
        return simplejson.dumps(ret)
    
    
    class Meta:
        ordering = ('when_created',)
    
class StoredHttpParam(models.Model):
    name = models.CharField(max_length=32)
    value = models.TextField(default='')
    request = models.ForeignKey(StoredHandlerRequest)
    
    def __unicode__(self):
        return "%s %s: %s=%s" %(self.request.method, self.request.path, self.name, self.value)
    
    def dict(self):
        return {'name': self.name, 'value':self.value}
    
class APIChangeLogEntry(models.Model):
    description = models.CharField(max_length=256)
    entered_by = models.CharField(max_length=256, default="Joel")
    when_created = models.DateTimeField(default=datetime.datetime.utcnow, editable=False)
    
    def __unicode__(self):
        return "%s -- %s" % (self.description, self.entered_by)
    
    class Meta:
        verbose_name = "API ChangeLog Entry"
        verbose_name_plural = "API ChangeLog Entries"
        ordering = ('-when_created',)
        


class BaseGeoModel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=512)
    street = models.CharField(max_length=256, default='', blank=True)
    cross_street = models.CharField(max_length=256, default=' ', blank=True)
    city = models.CharField(max_length=256, default='', blank=True)
    state = models.CharField(max_length=32, default='', blank=True,choices = consts.SUPPORTED_STATES_CHOICES)
    country = models.CharField(max_length=256, default='', blank=True)
    zip = models.CharField(max_length=10, default='', blank=True)
    geolocation = models.PointField(unique=True, null=True, blank=True)
    objects = models.GeoManager()
    
    class Meta:
        abstract = True
    
    def dict(self):
        ret = utils.toDict(self)
        del ret['geolocation']
        del ret['street']
        del ret['city']
        del ret['zip']
        del ret['country']
        del ret['cross_street']
        del ret['state']
        ret['address'] = self.address
        return ret
    
    
    @property
    def address(self):
        return "%(street)s\n%(city)s, %(state)s %(zip)s, %(country)s" % {'street': self.street,
                                                                         'city' : self.city,
                                                                         'state': self.state,
                                                                         'zip': self.zip, 'country': self.country}
        
    def __unicode__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """
        Overload save function to grab the geo location for this address
        so it is readily available later
        """
        geo_code = list(utils.GeoCode(self.address).getCoords())
        geo_code.reverse()
        if geo_code:
            self.geolocation = utils.location_from_coords(*geo_code)
        super(BaseGeoModel, self).save(*args, **kwargs) #IGNORE:E1002 -- parent is not an old-style class
