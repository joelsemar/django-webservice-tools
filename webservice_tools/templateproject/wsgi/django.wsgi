import os, sys
sys.path.insert(0, '/var/www/{{servername}}')
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()    
