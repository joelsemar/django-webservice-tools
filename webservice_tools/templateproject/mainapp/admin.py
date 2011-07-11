from django.contrib import admin
from mainapp import models
from django.db.models.base import ModelBase
from django.contrib.sites.models import Site
from django.contrib.auth.models import Group

for model_name in dir(models):
    m = getattr(models, model_name)
    if isinstance(m, ModelBase):
        try:
            admin.site.register(m)
        except admin.sites.AlreadyRegistered:
            pass 

admin.site.unregister([Site, Group])
