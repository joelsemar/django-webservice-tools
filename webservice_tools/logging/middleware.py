from webservice_tools.logging import logging
from webservice_tools.utils import toDict
class LoggingMiddleware(object):
    
    def process_response(self, request, response):
        if 'text/html' in response['Content-Type']:
            return response
        
        log = "-------------------------------------\n%(request)s\nURL: %(url)s\nRESPONSE\n%(response)s\n-------------------------------------\n" 
        msg = ""
        if request.GET:
            msg += "REQUEST GET: %s" % toDict(request.GET)
        if request.POST:
            msg += "REQUEST POST: %s" % toDict(request.POST)
            
        logging.debug(log % {'request': msg,
                             'response': response,
                             'url': request.path})
        return response
