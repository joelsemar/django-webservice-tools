from webservice_tools.response_util import ResponseObject
from django.conf import settings
class ProvideResponse(object):
    
    
    def process_view(self, request, view, args, kwargs):
        """
        Provides a response object for the view based on the 'accept' header
        Optionally provides the docstring to the view in debug mode
        """
        
        if kwargs.get('dataFormat') or 'admin' in request.path:
            return None
        
        if 'xml' in request.META.get('HTTP_ACCEPT', 'json'):
            data_format = 'xml'
        else:
            data_format = 'json'
        
        kwargs['response'] = ResponseObject(dataFormat=data_format)
        if settings.DEBUG:
            if hasattr(view, 'callmap'):
                doc = getattr(view.handler, view.callmap[request.method]).func_doc
            else:
                doc = view.func_doc
            if data_format == 'json':
                doc = doc.replace('\n', '<br/>')
            kwargs['response'].doc=doc
        
        return None
