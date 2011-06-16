from webservice_tools.response_util import ResponseObject
from webservice_tools.models import StoredHandlerResponse
from django.conf import settings
class ProvideResponse(object):
    
    
    def process_view(self, request, view, args, kwargs):
        """
        Provides a response object for the view based on the 'accept' header
        Optionally provides the docstring to the view in debug mode
        """
        data_format = None
        accept_header = request.META.get('HTTP_ACCEPT', '')
        if 'text/xml' in accept_header and 'html' not in accept_header:
            data_format = 'xml'
        elif 'application/json' in accept_header:
            data_format = 'json'
        
        data_format = data_format or request.GET.get('format')
        
        if ('html' in accept_header or 'admin' in request.path or 'static' in request.path) and not data_format:
            return None
        
        if getattr(settings, 'MESSAGES_ENABLED', False):
            kwargs['response'] = ResponseObject(request=request)
        else:
            kwargs['response'] = ResponseObject()
        if request.META.get("HTTP_SHOW_DOC"):
            if hasattr(view, 'callmap'):
                doc = getattr(view.handler, view.callmap[request.method]).func_doc
            else:
                doc = view.func_doc
            if data_format == 'json' and doc:
                doc = doc.replace('\n', '<br/>')
            kwargs['response'].doc=doc
        request.handler_id = str(view.handler.__class__)
        
        return None




class StoreResponse(object):
    
    def process_response(self, request, response):
        if request.META.get('HTTP_STORE_RESPONSE'):
            if hasattr(request, 'handler_id'):
                handler_id = request.handler_id
                stored_response = StoredHandlerResponse.objects.get_or_create(handler_id=handler_id, method=request.method)[0]
                stored_response.response = response.content
                stored_response.save()
        return response