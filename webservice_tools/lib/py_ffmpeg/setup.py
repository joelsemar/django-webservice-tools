# -*- coding: utf-8 -*-
import os
from distutils.core import setup
from distutils.extension import Extension
from os.path import join as path_join
from sys import platform

## Try to locate source if necessary
##
#sources = ['py_ffmpeg.c']
##headers = []
#for root, dir, files in os.walk('./include'):
#    for file in files:
#        if '.c' in file:
#            sources.append(os.path.join(root,file))
# #       if '.h' in file:
#  #          headers.append(os.path.join(root,file))
#
#ext_modules=[ Extension('py_ffmpeg', sources=sources,
#   #                     headers = headers,
#                   include_dirs = ['./include/'],) 
#                ]
# 
#
#setup(
#    name = 'test',
#    version = ".1.0",
#    ext_modules = ext_modules
#)

setup(
        name="py_ffmpeg",
        ext_modules=[ 
          Extension("py_ffmpeg", ["py_ffmpeg.c"],
              include_dirs=["/usr/include/libavcodec/", "/usr/include/libavformat", "/usr/include/libavutil", "/usr/include/libswscale"],
              library_dirs=["/usr/lib/", "/usr/local/lib"],
              libraries=["avformat", "avcodec", "swscale", "avutil"])
          ],
        #cmdclass={'build_ext': build_ext},
        version="0.2.2",
        author="Joshua Semar",
        author_email="semarj@gmail.com",
        url="",
      )