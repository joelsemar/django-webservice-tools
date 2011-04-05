from django.contrib import admin
from django import forms
from django.db.models.base import ModelBase
from webservice_tools.apps.user import models
for model_name in dir(models):
    m = getattr(models, model_name)
    if isinstance(m, ModelBase):
        try:
            admin.site.register(m)
        except admin.sites.AlreadyRegistered:
            pass

admin.site.unregister(models.BaseProfile)