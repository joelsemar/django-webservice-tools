# -*- coding: utf-8 -*-
import os
from distutils.core import setup
from distutils.extension import Extension
from os.path import join as path_join
from sys import platform

setup(
        name="py_ffmpeg",
        ext_modules=[ 
          Extension("py_ffmpeg", ["py_ffmpeg.c"],
              include_dirs=["/usr/local/include/libavcodec/", "/usr/local/include/libavformat", "/usr/local/include/libavutil", "/usr/local/include/libswscale"],
              library_dirs=["/usr/local/lib"],
              libraries=["avformat", "avcodec", "swscale", "avutil", "mp3lame"])
          ],
        #cmdclass={'build_ext': build_ext},
        version="0.2.2",
        author="Joshua Semar",
        author_email="semarj@gmail.com",
        url="",
      )
