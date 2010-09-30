from django.contrib.gis.db import models
from django.core.exceptions import ObjectDoesNotExist
class SoftDeleteManager(models.Manager):
    """
    Model manager that auto filters out instances with <field>=False
    """
    def __init__(self, field='disabled'):
        self.queryKwargs = {field: False}
        super(SoftDeleteManager, self).__init__()
        
    
    def get_query_set(self):
        return super(SoftDeleteManager, self).get_query_set().filter(**self.queryKwargs)
    
    
    def all_with_deleted(self):
        #returns all objects, deleted or not
        return super(SoftDeleteManager, self).get_query_set()
    
    
    def deleted_set(self):
        #returns only deleted objects
        return super(SoftDeleteManager, self).get_query_set().exclude(**self.queryKwargs)
    
    
def isDirty(model, fieldName):
    """
    Compares a given model instance with the DB and tells you whether or not it has been altered since the last save()
    """
    entryInDB = None
    try:
        entryInDB = model.__class__.objects.get(id=model.id)
    except ObjectDoesNotExist:
        raise Exception("A serious error has occurred in db_utils.isDirty(). A model instance was passed that doesn't exist.")
    
    return entryInDB.__dict__[fieldName] != model.__dict__[fieldName]    
