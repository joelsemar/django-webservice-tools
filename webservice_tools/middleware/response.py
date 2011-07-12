import re
from webservice_tools.response_util import ResponseObject
from webservice_tools.models import StoredHandlerResponse, StoredHandlerRequest, StoredHttpParam
from webservice_tools.doc_generator.server_declaration import ServerDeclaration
from django.conf import settings
from django.db import transaction

class ProvideResponse(object):
    
    def process_view(self, request, view, args, kwargs):
        """
        Provides a response object for the view based on the 'accept' header
        Optionally provides the docstring to the view in debug mode
        """
        data_format = None
        accept_header = request.META.get('HTTP_ACCEPT', '')
        
        if not hasattr(view, 'callmap'):
            return None
        
        request.handler_id = str(view.handler.__class__)
        
        if getattr(settings, 'MESSAGES_ENABLED', False):
            kwargs['response'] = ResponseObject(request=request)
        else:
            kwargs['response'] = ResponseObject()
         
        
        return None




class DocBuilder(object):
    
    @transaction.commit_on_success
    def process_view(self, request, view, args, kwargs):
        if request.META.get('HTTP_STORE_AS_TEST') and \
          hasattr(view, 'callmap') and hasattr(request, 'handler_id'):
            server_declaration = ServerDeclaration()
            handlers = server_declaration.handler_list
            handler_data = [h for h in handlers if h['name'] == re.sub('Handler$', '', view.handler.__class__.__name__)]
            method_data = [m for m in handler_data[0]['methods'] if m['request_method'] == request.method]
            
            stored_handler_request = StoredHandlerRequest.objects.create(path=request.path, method=request.method,
                                                                          handler_id=request.handler_id, test=True)
                
            for param in method_data[0]['params']:
                
                name = param['name']
                if name in getattr(request, request.method):
                    value = str(getattr(request, request.method).get(name))
                    StoredHttpParam.objects.create(name=name, value=value, request=stored_handler_request)

    
    def process_response(self, request, response):
        if request.META.get('HTTP_STORE_RESPONSE'):
            if hasattr(request, 'handler_id'):
                handler_id = request.handler_id
                stored_response = StoredHandlerResponse.objects.get_or_create(handler_id=handler_id, method=request.method)[0]
                stored_response.response = response.content
                stored_response.save()
        return response
