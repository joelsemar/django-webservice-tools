import re
import datetime
from django.contrib.gis.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.query import QuerySet
from django.db.models.fields.files import ImageField, ImageFieldFile
from django.conf import settings

#may or may not be installed on the server
try:
    from PIL import Image
except:
    pass

class SoftDeleteManager(models.GeoManager):
    """
    Model manager that auto filters out instances with <field>=False
    """
    def __init__(self):
        self.queryKwargs  = {'disabled': False}
        super(SoftDeleteManager, self).__init__()
        
    
    def get_query_set(self):
        return super(SoftDeleteManager, self).get_query_set().filter(**self.queryKwargs)
    
    
    def all_with_deleted(self):
        #returns all objects, deleted or not
        return super(SoftDeleteManager, self).get_query_set()
    
    
    def deleted_set(self):
        #returns only deleted objects
        return super(SoftDeleteManager, self).get_query_set().exclude(**self.queryKwargs)
    

class ExpirationManager(models.Manager):
    """
    Manager auto filters out instances that expired, 
    Using the provided DateTimeField, (defaults to 'expires') doesn't get return if that time has passed
    """
    def get_query_set(self):
        now = datetime.datetime.utcnow()
        return super(ExpirationManager, self).get_query_set().filter(**{'expires__gte': now})

    def all_with_expired(self):
        #returns all objects, expired or not or not
        return super(ExpirationManager, self).get_query_set()
    

def isDirty(model, fieldName):
    """
    Compares a given model instance with the DB and tells you whether or not it has been altered since the last save()
    """
    entryInDB = None
    try:
        entryInDB = model.__class__.objects.get(id=model.id)
    except ObjectDoesNotExist:
        raise Exception("A serious error has occurred in db_utils.isDirty(). A model instance was passed that doesn't exist.")
    return re.sub('[\r\n\ ]+', '', entryInDB.__dict__.get(fieldName, 'none')) != re.sub('[\r\n\ ]+', '', model.__dict__.get(fieldName, 'none'))    



class ThumbFieldFile(ImageFieldFile):
    
    def save(self, *args, **kwargs):
        rotation =  kwargs.get('rotation')
        if 'rotation' in kwargs:
            del kwargs['rotation']
            
        super(ImageFieldFile, self).save(*args, **kwargs)
        filename = self.path
        imageFile = Image.open(filename)
        imageFile.thumbnail(settings.DEFAULT_THUMB_SIZE, Image.ANTIALIAS)
        
        if rotation:
            try:
                rotation = int(rotation)
                if rotation  in [90, 180, 270]:
                    imageFile = imageFile.rotate(rotation)
            except ValueError:
                pass
        imageFile.save(filename)
        
class ThumbField(ImageField):
    
    attr_class = ThumbFieldFile


#so south doesn't choke on our custom field
from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ['webservice_tools.db_utils.ThumbField'])
