import re
import copy
import string
from ripplr import handlers
from piston.handler import HandlerMetaClass 
from piston.doc import HandlerDocumentation
from django.template import Template, Context
from django.conf import settings
available_methods = ['create', 'read', 'update', 'delete']
type_mappings = {'date': 'xsd:date',
                 'string': 'xsd:string',
                 'integer': 'xsd:integer',
                 'float': 'xsd:float',
                 'double': 'xsd:double',
                 'bool': 'xsd:boolean',
                 'url': 'xsd:anyURI'}

from ripplr import handlers as module, views
"""
TODO: fix up field creation as per conversation with david
POST: no fields
GET:  only id field contributes to fields
UPDATE: all fields
DELETE: same as GET
Any return values create field (maybe manually denotated?
"""
VAR_REGEX = r'\@[\w]+\ \[[\w\[\]]+\]\ .+' # @parameter [type] some comment

def main():
    ret = {'iface': settings.INTERFACE,
           'resources': []}
    
    for name in dir(module):
        try:
            handler = HandlerADL(module, name)
        except HandlerTypeError:
            continue
        ret['resources'].append(handler)
    
    template = Template(open('template.xml').read())
    context = Context(ret)
    outputfile = open('output.xml', 'w')
    outputfile.write(template.render(context))
    return ret

    
class HandlerADL(object):
    
    def __init__(self, module, name):
        self.name = re.sub('Handler', '', name)
        self.handler = getattr(module, name)
        if type(self.handler) is not HandlerMetaClass or name == 'BaseHandler':
            raise HandlerTypeError
        self.handler_docs = HandlerDocumentation(self.handler)
        self.model_fields = []
        if hasattr(self.handler, 'models'):
            self.model_fields = [field.get_attname() for model in self.handler.models  for field in model._meta._fields()]
        else:
            self.model_fields = [str(field.get_attname()) for field in self.handler.model._meta._fields()]
        self.fields = self._get_base_fields()
        self.methods = []
        for method in self.handler_docs.get_methods():
            docstring = method.get_doc()
            api_handler = self._get_method_api_handler(docstring)
            if not api_handler:
                continue
            http_method = api_handler.get('method').upper()
            method_params = self._get_method_params(docstring, http_method, api_handler) 
            if not method_params:
                continue
            
            self.methods.append({'name': method.name,
                                 'params': method_params,
                                 'return_path': http_method in ['POST', "PUT", 'DELETE'] and 'success' or 'data.%s' % self.name.lower(),
                                 'http_method': http_method,
                                 'comment': api_handler.get('comment', '').strip(),
                                 'url': api_handler.get('url')})
    
    
    def __getitem__(self, key):
        if key in ['id', 'fields', 'methods']:
            return getattr(self, key)
        raise KeyError

    
    def _get_base_fields(self):
        docstring = self.handler.__doc__
        if not docstring:
            return []
        field_declarations = re.findall(VAR_REGEX, docstring)
        fields = [self._get_dict_from_var_declaration(declaration) for declaration in field_declarations] 
        return fields 
    
    
    def _get_method_params(self, docstring, http_method, api_handler):
        
        ret = []
        if not docstring:
            return ret

        variable_declarations = re.findall(VAR_REGEX, docstring)
        for declaration in variable_declarations:
            param = self._get_dict_from_var_declaration(declaration)
            if param['key'] in self.model_fields:
                param['field'] = param['key']
                fieldDict = copy.deepcopy(param)
                existing_field = filter(lambda f: f['name'] == fieldDict['name'], self.fields)
                if existing_field:
                    if http_method in ('POST', 'PUT', 'DELETE') and existing_field[0]['access'] != 'key':
                        existing_field[0]['access'] = 'rw'
                else:
                    fieldDict['access'] = http_method in ('POST', 'PUT', 'DELETE') and 'rw' or 'ro'
                    self.fields.append(fieldDict)
            if "{%s}" % param['key'] in api_handler.get('url', ''):
                param['style'] = 'template'
            if re.search('(optional)', declaration):
                param['required'] = '0'
            else:
                param['required'] = '1' 
            ret.append(param)
        
        return ret

    
    def _get_dict_from_var_declaration(self, declaration):
        param = re.search(r'^\@(?P<name>[\w]+)[\ ]+\[(?P<type>[\w\[\]]+)\]', declaration).groupdict()
        param['type'] = type_mappings.get(param['type'], param['type'])
        param['key'] = param['name']
        param['access'] = 'ro'
        if '_' in param['name']:
            words = param['name'].split('_')
            # use mixedCase for name instead of under_score, fooId also becomes fooID
            param['name'] = re.sub('Id', 'ID', words[0] + ''.join(string.capwords(s) for s in words[1:]))
        
        if 'id' in param['name'].lower():
            param['access'] = 'key'
        return param
    
    
    def _get_method_api_handler(self, docstring):
        if not docstring:
            return {}
        api_handler = re.search(r'(?P<comment>[\w.\ \n\/]+)?api handler\: (?P<method>post|put|get|delete)[\ ](?P<url>.+)', docstring, flags=re.IGNORECASE)
        if api_handler:
            return api_handler.groupdict()
    


class HandlerTypeError(Exception):
    """
    Just an exception raised if the passed object isn't a handler
    """
    pass
    
