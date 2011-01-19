from webservice_tools.logging import logging
from webservice_tools.utils import toDict
import datetime
class LoggingMiddleware(object):
    
    def process_response(self, request, response):
        if '/static/' in request.path:
            return response
        
        if 'html' in response['Content-Type'] or 'javascript' in response['Content-Type']:
            return response
        
        log = "-------------------------------------\n%s(timestamp)s\n%(request)s\nHANDLER: %(method)s %(url)s\nRESPONSE\n%(response)s\n-------------------------------------\n" 
        msg = ""
        try:
            if request.GET:
                msg += "REQUEST GET: %s" % toDict(request.GET)
            if request.POST:
                msg += "REQUEST POST: %s" % toDict(request.POST)
            if request.FILES:
                msg += 'FILES: %s' % ','.join([f.name for f in request.FILES.itervalues()])
        except:
            pass
        
        headers = ''
        for k, v in request.META.iteritems():
            headers += '%s: %s\n' % (k,v )
        logging.debug(log % {'request': msg,
                             'method': request.method,
                             'response': str(response)[:5000],
                             'url': request.path,
                             'timestamp': datetime.datetime.utcnow()})
        return response
