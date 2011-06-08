import re
from webservice_tools.utils import Resource
call_map = {'GET': 'read', 'POST': 'create', 
            'PUT': 'update', 'DELETE': 'delete'}
#VAR_REGEX = r'^[@][\w]+\ \[[\w\[\]]+\]\ .+' # @parameter [type] some comment
VAR_REGEX = ex = '^\s+\@.+'
class ServerDeclaration():
    
    def __init__(self):
        self.handlers = self.crawl_urls()
        self.handler_list = []
        for handler in self.handlers:
            self.handler_list.append({'name': re.sub('Handler$', '', handler.__class__.__name__),
                                      'methods': self.get_methods(handler)})  
        
        self.handler_list.sort(key=lambda x: x['name'])
    
    def get_methods(self, handler):
        ret = []
        for request_method in handler.allowed_methods:
            method_name = call_map[request_method]
            method = getattr(handler, method_name)
            docstring = method.__doc__
            auth_required = False
            if hasattr(method, 'authentication_required'):
                auth_required=True
            api_handler = self._get_method_api_handler(docstring)
            ret.append({'name': method_name, 'request_method': request_method,
                        'url': api_handler.get('url'), 'comment': api_handler.get('comment'),
                        'params': self._get_method_params(docstring), 'auth_required': auth_required})
        return ret
            
    def _get_method_api_handler(self, docstring):
        if not docstring:
            return {}
        
        api_handler = re.search(r'api handler\:? (?P<method>post|put|get|delete)[\ ](?P<url>.+)', docstring, flags=re.IGNORECASE)
        if api_handler:
            ret =  api_handler.groupdict()
            comment = re.search(r'^(?P<comment>.*)api handler', docstring, flags= re.IGNORECASE|re.DOTALL)
            if comment:
                ret['comment'] = comment.groupdict()['comment'].replace('\n', '<br/>')
            return ret
        return {}
    
    def _get_method_params(self, docstring):
        
        ret = []
        if not docstring:
            return ret

        variable_declarations = re.findall(VAR_REGEX, docstring, flags=re.MULTILINE|re.DOTALL)
        if variable_declarations:
            variable_declarations = [f for f in variable_declarations[0].split('    @') if f.strip()]
        for declaration in variable_declarations:
            ret.append(self._get_dict_from_var_declaration(declaration))
        return ret
    
    def _get_dict_from_var_declaration(self, declaration):
        param = re.search(r'^(?P<name>[\w]+)[\ ]+\[(?P<type>[\w\[\]]+)\][\ ]*(?P<comment>.*)', declaration, flags=re.DOTALL)
        if not param:
            return {}
        param = param.groupdict()
        param['comment'] = re.sub('\n', '<br />', param['comment'])
        if re.search('(optional)', declaration):
            param['comment'] = re.sub('\(optional\)', '', param['comment'])
            param['required'] = '0'
        else:
            param['required'] = '1' 
        return param


    def crawl_urls(self):
        ret = []
        handler_names = []
        import urls
        all = []
        def _crawl_urls(urllist):
            for entry in urllist:
                if hasattr(entry, 'url_patterns'):
                    _crawl_urls(entry.url_patterns)
                else:
                    callback = entry._get_callback()
                    all.append(entry)
                    if isinstance(callback, Resource):
                        handler_name =  callback.handler.__class__.__name__
                        if handler_name not in handler_names and not getattr(callback.handler.__class__, 'internal', False):
                            handler_names.append(handler_name)
                            ret.append(callback.handler)
        
        _crawl_urls(urls.urlpatterns)
        return ret
            
        