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
        if 'text/xml' in accept_header and 'html' not in accept_header:
            data_format = 'xml'
        elif 'application/json' in accept_header:
            data_format = 'json'
        
        data_format = data_format or request.GET.get('format') or request.POST.get('format') 
        
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
            kwargs['response'].doc = doc
        if hasattr(view, 'callmap'):
            request.handler_id = str(view.handler.__class__)
        
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
