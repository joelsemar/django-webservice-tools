from datetime import datetime, timedelta
import sys
import re
import os

from django.contrib.gis.db import models
from django.contrib.auth.models import User
from django.db.models.base import ModelBase

from webservice_tools import utils

# Create your models here.



























#ALL DEFINITION EOF
module_name = globals().get('__name__')
models = sys.modules[module_name]
models._all_ = []
for model_name in dir():
    m = getattr(models, model_name)
    if isinstance(m, ModelBase) and not m._meta.abstract:
        models._all_.append(model_name)