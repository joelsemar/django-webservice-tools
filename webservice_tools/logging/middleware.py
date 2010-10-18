from webservice_tools.logging import logging
from webservice_tools.utils import toDict
class LoggingMiddleware(object):
    
    def process_response(self, request, response):
        if 'html' in response['Content-Type'] or 'javascript' in response['Content-Type']:
            return response
        
        log = "-------------------------------------\n%(request)s\n%(headers)s\nHANDLER: %(method)s %(url)s\nRESPONSE\n%(response)s\n-------------------------------------\n" 
        msg = ""
        try:
            if request.GET:
                msg += "REQUEST GET: %s" % toDict(request.GET)
            if request.POST:
                msg += "REQUEST POST: %s" % toDict(request.POST)
            if request.FILES:
                msg += 'FILES: %s' % ','.join([f.name for f in request.FILES.iterkeys()])
        except:
            pass
        
        headers = ''
        for k, v in request.META.iteritems():
            headers += '%s: %s\n' % (k,v )
        logging.debug(log % {'request': msg,
                             'headers': headers, 
                             'method': request.method,
                             'response': str(response)[:5000],
                             'url': request.path})
        return response
