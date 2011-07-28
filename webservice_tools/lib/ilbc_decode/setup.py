from distutils.core import setup, Extension

ilbc = Extension('py_ilbc',
                    sources = ['py_ilbc.c', 'FrameClassify.c', 'LPCdecode.c', 'LPCencode.c', 'StateConstructW.c', 'StateSearchW.c', 'anaFilter.c', 'constants.c', 'createCB.c', 
                               'doCPLC.c', 'enhancer.c', 'filter.c', 'gainquant.c', 'getCBvec.c', 'helpfun.c', 'hpInput.c', 'hpOutput.c', 'iCBConstruct.c', 'iCBSearch.c', 'iLBC_decode.c', 
                               'iLBC_encode.c', 'lsf.c', 'packing.c', 'syntFilter.c'])

setup (name = 'ApILBC',
       version = '.2',
       description = 'This is an Appiction ILBC Package',
       ext_modules = [ilbc])

