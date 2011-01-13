import simplejson
from django import dispatch
from django.core import serializers
from django.core.serializers.json import DateTimeAwareJSONEncoder
from django.http import HttpResponse
from django.db import models
from django.contrib.auth.models import User
from webservice_tools.logging import logging
import utils
from xml.dom import minidom
JSON_INDENT = 4

XMLSerializer = serializers.get_serializer("xml")
JSONSerializer = serializers.get_serializer('json')

message_sent = dispatch.Signal(providing_args=['message'])

class ResponseObject():
    """
    A generic response object for generating and returning api responses
    """
    def __init__(self, dataFormat='json', request=None):
        self._errors = []
        self._request = request
        self._messages = []
        self.success = True
        self._data = {}
        self._status = 200
        self._dataFormat = dataFormat
        self.doc = None
        self.headers = {}
        
        if self._request:
            message_sent.connect(self.message_callback, sender=None, dispatch_uid='response_receiver')
    
    
    
    def set_headers(self, headers):
        for k, v in headers.items():
            self.headers[k] = v
    
    
    def addErrors(self, errors, status=500):
        
        self.success = False
        
        if status:
            self._status = status
            
        if isinstance(errors, basestring):
            #just a single error
            self._errors.append(errors)
            return
        
        elif isinstance(errors, list):
            # a list of errors
            for error in errors:
                self._errors.append(error)
            return
        raise TypeError("Argument 'errors' must be of type 'string' or 'list'")
    
    
    def message_callback(self, signal, sender, **kwargs):
        message = kwargs.get('message', '')
        if self._request.user.id == sender.id:
            self.addMessages(message)
        
    
    def addMessages(self, messages):
        self.success = False
        if isinstance(messages, basestring):
            #just a single message
            self._messages.append(messages)
            return
        
        elif isinstance(messages, (list, tuple)):
            # a list of errors
            for message in messages:
                self._messages.append(message)
            return
        self._messages.append(messages)

    
    def set(self, **kwargs):
        self._data.update(kwargs)
    
    def __setitem__(self, key, value):
        self._data[key] = value
    
    def __getitem__(self, key):
        return self._data[key]
        
    def get(self, key):
        return self._data[key]
    
    def setStatus(self, status):
        assert isinstance(status, int)
        self._status = status
    
    
    def send(self, messages=None, errors=None, status=None):
        
        
        if errors:
            self.addErrors(errors)
        
        if status:
            self.setStatus(status)
        
        if messages:
            self.addMessages(messages)
        
        responseDict = {}
        responseDict['data'] = {}
        responseDict['errors'] = self._errors
        responseDict['success'] = self.success
        if self._messages:
            responseDict['messages'] = self._messages
        if self.doc:
            responseDict['doc'] = self.doc
        
        
        return responseDict
        
        """
        After this is a bunch of dead code, for now we will default back to using piston's emmiter
        
        """
        
        
        if self._dataFormat == 'json':
            return self._sendJSON(responseDict)
        
        else:
            return self._sendXML(responseDict)
        
        
    def _sendJSON(self, responseDict):
        responseDict = self._prepareData(responseDict, JSONSerializer())
        content = simplejson.dumps(responseDict, cls=DateTimeAwareJSONEncoder,
                                   ensure_ascii=True, indent=JSON_INDENT)
        http_response = HttpResponse(content, mimetype='application/json', status=self._status)
        if self.headers:
            for k, v in self.headers.items():
                http_response[k] = v 
        return http_response
        
    def _sendXML(self, responseDict):
        responseDict = self._prepareData(responseDict, XMLSerializer())
        content = utils.toXML(responseDict, 'response')
        content = utils.escape_xml(content)
        content = utils.prettyxml(minidom.parseString(content))
        http_response = HttpResponse(content, mimetype='text/xml', status=self._status)
        
        if self.headers:
            for k, v in self.headers:
                http_response[k] = v 
        return http_response
        
    
    def _prepareData(self, responseDict, serializer):
        for key, value in self._data.iteritems():
            if isinstance(value, models.query.QuerySet):
                responseDict['data'][key] = serializer.serialize(value)
            elif isinstance(value, (list, tuple)):
                responseDict['data'][key] = [utils.toDict(o) for o in value]
            else:
                responseDict['data'][key] = utils.toDict(value)
        return responseDict
    
    
