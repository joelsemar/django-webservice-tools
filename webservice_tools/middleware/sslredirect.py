# -*- coding: utf-8 -*-
#############################
#MODULE DEPENDENCIES
#############################
#General deps
from django.conf import settings
from django.http import HttpResponsePermanentRedirect, get_host

#############################
#MODULE-LEVEL VARIABLES
#############################
SSL = 'SSL'

#############################
#MODULE FUNCTIONALITY
#############################
class SSLRedirect:
    """
    This middleware answers the problem of redirecting to (and from) a SSL secured path by stating what
    paths should be secured in urls.py file. To secure a path, add the additional view_kwarg 'SSL':True to
    the view_kwargs.
    """
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        if SSL in view_kwargs:
            secure = view_kwargs[SSL]
            del view_kwargs[SSL]
        else:
            secure = None

        #if we're running via the command line (dev testing) then disable secure mode (as runserver doesn't support that)
        if not getattr(settings, 'SECURE', False):
            secure = False

        #also support SSL set to None to not change whatever the request came in as
        if     secure != None \
           and secure != self._is_secure(request, secure):
            return self._redirect(request, secure)


    def _is_secure(self, request, secure):
        if request.is_secure():
            return True
        #this will catch cases where the invocation was not over SSL
        return request.META.get('HTTP_X_FORWARDED_SSL') == 'on'
        
        #also, skip SSL in cases where we're accessed from the internal network
        if 'HTTP_X_FORWARDED_FOR' not in request.META:
            #we just want to bypass auto redirections (in either case, both secure->nonsecure, and nonsecure->secure)
            return secure

        return False


    def _redirect(self, request, secure):
        protocol = secure and "https" or "http"
        newurl = "%s://%s%s" % (protocol, get_host(request), request.get_full_path())
        if settings.DEBUG and request.method == 'POST':
            raise RuntimeError, \
        """Django can't perform a SSL redirect while maintaining POST data.
           Please structure your views so that redirects only occur during GETs."""

        return HttpResponsePermanentRedirect(newurl)
