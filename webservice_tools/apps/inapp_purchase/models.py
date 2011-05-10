import datetime
from django.conf import settings
from django.db import models

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
        
    def save(self, *args, **kwargs):
        if not self.id:
            self.when_created = datetime.datetime.utcnow()
            
        super(AppleReceipt, self).save(*args, **kwargs)
