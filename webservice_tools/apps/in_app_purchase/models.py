import datetime
from django.conf import settings
from django.db import models
import sys
from django.db.models.base import ModelBase

class AppleReceipt(models.Model):
    """
    Receipt dictionary received from Apple
    everything is the same as what apple sends with the exception of our id,
    and a foreign to the userprofile that made the purchase
    """
    id = models.AutoField(primary_key=True)
    item_id = models.CharField(max_length=32)
    quantity = models.PositiveIntegerField(default=1)
    product_id = models.CharField(max_length=512)
    transaction_id = models.CharField(max_length=512, unique=True)
    original_transaction_id = models.CharField(max_length=512)
    purchase_date = models.DateTimeField()
    original_purchase_date = models.DateTimeField()
    app_item_id = models.CharField(max_length=512)
    version_external_identifier = models.CharField(max_length=512, null=True)
    bid = models.CharField(max_length=512)
    bvrs = models.CharField(max_length=512)
    profile = models.ForeignKey(settings.AUTH_PROFILE_MODULE)
    when_created = models.DateTimeField()
    
    class Meta:
        db_table = 'applereceipt'
        verbose_name = "Apple Receipt"
        verbose_name_plural = "Apple Receipts"
        
    def save(self, *args, **kwargs):
        if not self.id:
            self.when_created = datetime.datetime.utcnow()
            
        super(AppleReceipt, self).save(*args, **kwargs)


#ALL DEFINITION EOF
module_name = globals().get('__name__')
models = sys.modules[module_name]
models._all_ = []
for model_name in dir():
    m = getattr(models, model_name)
    if isinstance(m, ModelBase) and not m._meta.abstract:
        models._all_.append(model_name)