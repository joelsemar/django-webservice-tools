from django.contrib import admin
from django.db.models import get_models, get_app, get_model

APP_NAME = 'webservice_tools'
app_models = get_models(get_app(APP_NAME)) # Get all app models.
for model in app_models:
    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass