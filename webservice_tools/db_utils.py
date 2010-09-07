from django.contrib.gis.db import models

class SoftDeleteManager(models.Manager):
    """
    model manager that auto filters out instances with disabled=False
    """
    def __init__(self, field='disabled'):
        self.deletedField = field
        self.queryKwargs = {field: False}
        self.deletedQueryKwargs = {field: True}
        super(SoftDeleteManager, self).__init__()
        
    def get_query_set(self):
        return super(SoftDeleteManager, self).get_query_set().filter(**self.queryKwargs)
    def all_with_deleted(self):
        return super(SoftDeleteManager, self).get_query_set()
    def deleted_set(self):
        return super(SoftDeleteManager, self).get_query_set().filter(**self.deletedQueryKwargs)