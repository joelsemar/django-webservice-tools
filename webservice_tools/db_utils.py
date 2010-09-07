from django.contrib.gis.db import models

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