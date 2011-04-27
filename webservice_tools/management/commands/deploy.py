import os
import sys
import pydoc
from django.core.management.base import BaseCommand, CommandError
import subprocess
import pexpect
from django.conf import settings
class Command(BaseCommand):
    """
    """
    def handle(self, *args, **options):
        try:
            username = args[0]
        except IndexError:
            print "Error: No username specified for login to remote server."
            return
        server_name = settings.SERVER_NAME
        try:
            domain = args[1]
        except IndexError:
            domain = 'staging.appiction.com'
        command = 'cd /var/www/%s && sudo -u www-data git reset --hard && sudo -u www-data git pull && sudo ./manage.py migrate && sudo /etc/init.d/apache2 restart' % server_name
        p = pexpect.spawn('ssh -t %s@%s %s' % (username, domain, command))
        p.interact()
