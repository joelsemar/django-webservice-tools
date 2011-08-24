from exceptions import Exception
import os
from datetime import datetime
from webservice_tools import uuid

class ApMediaError(Exception):
    pass


class Element(object):
    """
    Basic element that can be used for single-function elements, or subclassed and override data_received to 
    increase functionality
    """
    _function = lambda x : x
    _connected_elements = []
        
    def __init__(self, function=None):
        self._connected_elements = []
        if function:
            self._function = function
    
    def send(self, data):
        for element in self._connected_elements:
            element.data_received(data)
    
    def data_received(self, data):
        """
        This should be overridden and end with a call to "self.send(your_modified_data)"
        """
        self.send(self._function(data))
    
    def connect(self, element):
        self._connected_elements.insert(0,element)

    def disconnect(self, element):
        self._connected_elements.remove(element)
        
    def finish(self):
        """
        Override this and cleanup/close files/flush buffers, then call self.finish_connected()
        """
        self.finish_connected()
        
    def finish_connected(self):
        for element in self._connected_elements:
            element.finish()

class Segmenter(Element):
    
    _buffer = ''
    _buffer_limit = 0
    _chunk_count = 0
    _use_chunks = False
    _max_chunks = 0
    
    def __init__(self, bytes=None, chunks=None, finish_passes_partials=True):
        super(Segmenter, self).__init__()
        self.finish_passes_partials = finish_passes_partials
        if bytes:
            self._buffer_limit = bytes
        elif chunks:
            self._max_chunks = chunks
            self._use_chunks = True
        else:
            raise ApMediaError("bytes or chunks must be provided")
    
    def data_received(self, data):
        self._buffer += data
        if self._use_chunks:
            self._chunk_count += 1
        self.check_buffer()
    
    def check_buffer(self):
        if not self._use_chunks and len(self._buffer) > self._buffer_limit:
            self.send(self._buffer[:self._buffer_limit])
            self._buffer = self._buffer[self._buffer_limit:]
            self.check_buffer()
        elif self._use_chunks and self._chunk_count == self._max_chunks:
            self.send(self._buffer)
            self._buffer = ''
            self._chunk_count = 0
        elif self._use_chunks and self._chunk_count > self._max_chunks:
            raise ApMediaError("More chunks than possible in segmenter")
            
    def finish(self):
        if self.finish_passes_partials:
            self.send(self._buffer)
        self.finish_connected()

