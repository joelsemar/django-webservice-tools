from django import template
from django.conf import settings
register = template.Library()
import os

@register.simple_tag
def load_all_js(path):
    ret = ''
    js_path = os.path.abspath(settings.STATIC_ROOT + '/js/' + path) 

    for root, _, files in os.walk(js_path):
        files.sort()
        for file in files:
            file_url = (root + '/' + file).split(settings.STATIC_URL)[1]
            ret += "<script type='application/javascript' src='%s%s'></script>" % (settings.STATIC_URL, file_url)
    
    return ret

        

