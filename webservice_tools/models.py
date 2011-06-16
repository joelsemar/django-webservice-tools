from django.db import models

class StoredHandlerResponse(models.Model):
    handler_id = models.CharField(max_length=128, db_index=True)
    response = models.TextField(default='')
    method = models.CharField(max_length=16)
    