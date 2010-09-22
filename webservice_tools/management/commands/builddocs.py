import os
import sys
import pydoc
from django.core.management.base import BaseCommand, CommandError
class Command(BaseCommand):
    def handle(self, *args, **options):
        moduleDir =  args[0]
        docDir =  args[1]
        origDir = os.getcwd() 
        sys.path.append(moduleDir)
        os.chdir(docDir)
        os.system('rm *.html')
        print 'Building docs..'
        pydoc.writedocs(moduleDir)
        os.chdir(moduleDir)
        os.system('git add .')
        os.chdir(origDir)
        
        
        
        