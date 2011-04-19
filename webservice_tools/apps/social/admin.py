from django.contrib import admin
from django import forms
from django.db.models.base import ModelBase
from webservice_tools.apps.social import models
for model_name in dir(models):
    m = getattr(models, model_name)
    if isinstance(m, ModelBase) and not m._meta.abstract:
        try:
            admin.site.register(m)
        except admin.sites.AlreadyRegistered:
            pass

