import os
import sys
import pexpect
import pxssh
import getpass
from optparse import OptionParser

class ApTaskManage(object):
    
    def __init__(self, settings):
        self.settings = settings
        
    
    def execute(self):
        usage = "usage: %prog <command> [options]"
        parser = OptionParser(usage)
        parser.add_option("-r", "--remote", action="store_true", dest="remote", \
                               help="execute the command  on the remote server", default=False)
        parser.add_option("-u", "--username", dest="username", help="Required when using remote commands.")
        parser.add_option("-d", "--domain", dest="domain")
        parser.add_option("-m", "--msg", dest="commit_message", help="Used for the commit and push command")
        parser.add_option("-p", "--project", dest="project_name", help="Used for cloning the repo")

        options, args = parser.parse_args()
        command = sys.argv[1]
        if options.remote or options.domain:
            if not options.username:
                sys.stderr.write("Error: No username specified for login to remote server.")
                sys.exit(1)
                
                 
            domain = options.domain or 'staging.appiction.com'
            if command == 'install_app':
                self.install_app(options, domain, options.username) 
            else:
                sys.stderr.write("Connecting to %s...\n" % domain)
                command_string = "cd /var/www/%s && ./ap_manage.py %s" % (self.settings.SERVER_NAME, command)
                if '-r' in sys.argv:
                    sys.argv.remove('-r')
                if '-d' in sys.argv:
                    sys.argv.remove('-d')
                if domain in sys.argv:
                    sys.argv.remove(domain)
                p = pexpect.spawn('ssh -t %s@%s %s %s' % (options.username, domain, command_string, ' '.join(sys.argv[2:])))
                p.interact()
        else:
            getattr(self, command)(options)       
    
    
    def install_app(self, options, domain, username):
        project_name = options.project_name
        if not project_name:
            sys.stderr.write("Please provide a project name for this project (-p FooProject)\n")
            sys.exit(1)
        server_name = self.settings.SERVER_NAME
        sys.stdout.write("Connecting to %s...\n" % domain)
        p = pxssh.pxssh()
        password = getpass.getpass("Password:")
        p.login(domain, username, password)
        p.prompt()
        p.sendline('cd /var/git/')
        p.prompt()
        p.sendline('sudo -u www-data git clone git@github.com:appiction/%s.git' % project_name)
        p.prompt()
        p.sendline('sudo ln -sf /var/git/%s/server/%s /var/www/%s' % (project_name, server_name, server_name))
        p.prompt()
        p.sendline('sudo ln -sf /usr/local/lib/python2.6/dist-packages/django/contrib/admin/media/ /var/www/%s/static/admin-media' % server_name)
        p.prompt()
        print p.before
        os.system('./ap_manage.py createdb -r -d %s -u %s' % (domain, username))
        os.system('./ap_manage.py apache_install -r -d %s -u %s' % (domain, username))

        
    
    def resetdb(self, options):
        db_settings = self.settings.DATABASES['default']
        os.system('sudo -u postgres drobdb %s' % db_settings.get('NAME'))
        self.createdb(options)
        
        
    def createdb(self, options):
        db_settings = self.settings.DATABASES['default']
        settings_dict = dict(db_name=db_settings.get('NAME'),
                             db_user=db_settings.get('USER'),
                             db_password=db_settings.get('PASSWORD'),)
        
        
        create_user_string = "CREATE USER  %(db_name)s WITH PASSWORD '%(db_password)s' --createdb" % settings_dict
        create_db_string = "sudo -u postgres createdb -E utf8 -T template_postgis -O %(db_user)s %(db_name)s" % settings_dict
        grant_string = "GRANT ALL PRIVILEGES ON DATABASE %(db_name)s to %(db_user)s" % settings_dict
        
        os.system("echo \"%s\" | sudo -u postgres psql" % create_user_string)
        os.system(create_db_string)
        os.system("echo '%s' | sudo -u postgres psql" % grant_string)
        
        if 'no-sync' not in sys.argv:
            self.syncdb(options)
            
        if 'no-migrate' not in sys.argv:
            self.migrate(options)
    
    def syncdb(self, options):
        os.system("sudo ./manage.py syncdb")

    def migrate(self, options):
        os.system("sudo ./manage.py migrate")
    
    def apache_install(self, options):
        server_name = self.settings.SERVER_NAME
        contents = "WSGIScriptAlias /%(server_name)s /var/www/%(server_name)s/wsgi/django.wsgi\nAlias /%(server_name)s/static /var/www/%(server_name)s/static/" \
                    % {'server_name': server_name}
        
        filename = "/var/www/%(server_name)s/wsgi/%(server_name)s.appconf" % {'server_name': server_name}
        os.system('sudo sh -c \'echo "%s" > "%s"\'' % (contents, filename))
        os.system('sudo ln -sf %s /etc/apache2/sites-available/%s' % (filename, filename.rpartition('/')[-1]))
        self.restart_apache(options)
    
    def restart_apache(self, options):
        os.system('sudo /etc/init.d/apache2 restart')
        
    def update(self, options):
        os.system('sudo -u www-data git reset --hard')
        os.system('sudo -u www-data git pull')
        os.system('sudo ./manage.py syncdb')
        os.system('sudo ./manage.py migrate')
        self.restart_apache(options)
    
    
    def updatetools(self, options):
        os.system('cd /var/git/django-webservice-tools && sudo -u www-data git reset --hard && sudo -u www-data git pull && sudo python setup.py install && sudo /etc/init.d/apache2 restart && cd -')
    
        
    def push(self, options):
        if not options.commit_message:
            sys.stderr.write("You must provide a commit message if you want to push")
            sys.exit(1)
        os.system('git commit -a -m "%s" && git push' % options.commit_message)
    
    
    def shell(self, options):
        os.system('./manage.py shell')