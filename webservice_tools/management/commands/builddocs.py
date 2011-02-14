import os
import sys
import pydoc
from django.core.management.base import BaseCommand, CommandError
class Command(BaseCommand):
    """
    Generates HTML docs for a project using pydoc
    Requires 2 arguments, the first is the path to the python package you want documented
    The second is the path to where you want the docs written to (will be created if not there)
    """
    def handle(self, *args, **options):
        moduleDir =  args[0]
        docDir =  args[1]
        origDir = os.getcwd() 
        sys.path.append(moduleDir)
        try:
            os.chdir(docDir)
        except OSError:
            os.mkdir(docDir)
            os.chdir(docDir)
        
        print 'Building docs...'
        pydoc.writedocs(moduleDir)
        # attempt to add the new docs to git
        os.chdir(moduleDir)
        os.system('find . -name *.html | xargs git add')
        os.chdir(origDir)
        
        
        
        
        