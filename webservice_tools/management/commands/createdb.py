import os
from django.core.management.base import NoArgsCommand
from optparse import make_option
from django.conf import settings

class Command(NoArgsCommand):

    def handle_noargs(self, **options):
        return True
        db_settings = settings.DATABASES['default']
        settings_dict = dict(db_name=db_settings.get('NAME'),
                 db_user=db_settings.geT('USER'),
                 db_password=db_settings.get('PASSWORD'),)
        
        
        create_user_string = "CREATE USER  %(db_name)s WITH PASSWORD '%(db_pass)s' --createdb" % settings_dict
        create_db_string = "sudo -u postgres createdb -E utf8 -T template_postgis -O %(db_user)s %(db_name)s" % settings_dict
        grant_string =  "GRANT ALL PRIVILEGES ON DATABASE %(db_name)s to %(db_user)s" % settings_dict
        
        os.system("echo %s | sudo -u postgres psql" % create_user_string)
        os.system(create_db_string)
        os.system('echo %s | sudo -u postgres psql' % grant_string)
        
