import simplejson
from django.core import serializers
from django.core.serializers.json import DateTimeAwareJSONEncoder
from django.http import HttpResponse
from django.db import models
from webservice_tools.logging import logging
import utils
from xml.dom import minidom
JSON_INDENT = 4

XMLSerializer = serializers.get_serializer("xml")
JSONSerializer = serializers.get_serializer('json')


class ResponseObject():
    """
    A generic response object for generating and returning api responses
    """
    def __init__(self, dataFormat='json'):
        self._errors = []
        self._messages = []
        self.success = True
        self._data = {}
        self._status = 200
        self._dataFormat = dataFormat
        self.doc = None
    
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
    
    
    def addMessages(self, messages):
        self.success = False
        
            
        if isinstance(messages, basestring):
            #just a single error
            self._messages.append(messages)
            return
        
        elif isinstance(messages, (list, tuple)):
            # a list of errors
            for message in messages:
                self._message.append(message)
            return
        raise TypeError("Argument 'messages' must be of type 'string' or 'list'")
    
    def set(self, **kwargs):
        self._data.update(kwargs)
    
    
    def __getitem__(self, key):
        return self._data[key]
        
    def get(self, key):
        return self._data[key]
    
    def setStatus(self, status):
        assert isinstance(status, int)
        self._status = status
    
    
    def send(self, messages=None, errors=None, status=None):
        
        if status:
            self.setStatus(status)
            
        if errors:
            self.addErrors(errors)
        
        if messages:
            self.addMessages(messages)
        
        responseDict = {}
        responseDict['data'] = {}
        responseDict['errors'] = self._errors
        responseDict['success'] = self.success
        responseDict['messages'] = self._messages
        if self.doc:
            responseDict['doc'] = self.doc
        
        
        if self._dataFormat == 'json':
            return self._sendJSON(responseDict)
        
        else:
            return self._sendXML(responseDict)
        
        
    def _sendJSON(self, responseDict):
        responseDict = self._prepareData(responseDict)
        content = simplejson.dumps(responseDict, cls=DateTimeAwareJSONEncoder,
                                   ensure_ascii=True, indent=JSON_INDENT)
        return HttpResponse(content, mimetype='application/json', status=self._status)
        
    def _sendXML(self, responseDict):
        responseDict = self._prepareData(responseDict)
        content =  utils.toXML(responseDict, 'response')
        content =  minidom.parseString(content).toprettyxml()
        return HttpResponse(content, mimetype='text/xml', status=self._status)
    
    
    def _prepareData(self, responseDict):
        for key, value in self._data.iteritems():
            if isinstance(value, (list, tuple, models.query.QuerySet)):
                responseDict['data'][key] = [utils.toDict(o) for o in value]
            else:
                responseDict['data'][key] = utils.toDict(value)
        return responseDict
    
