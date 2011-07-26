from distutils.core import setup, Extension

ilbc = Extension('py_ilbc_decode',
                    sources = ['py_ilbc_decode.c'],
                    include_dirs = ['/home/joshua/source/django-webservice-tools/webservice_tools/lib/ilbc_decode/'],
                    extra_compile_args = ['-l iLBC_decode.h'],
                    libraries = ["rt"])

setup (name = 'ApILBC',
       version = '.1',
       description = 'This is an Appiction ILBC Package',
       ext_modules = [ilbc])

