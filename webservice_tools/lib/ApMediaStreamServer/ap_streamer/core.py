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
    def noop(self, data):
        return data
    
    _function = noop
    
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
        Element.__init__(self)
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


class FileWriter(Element):
    """
    Send append=True or replace=True will assume only one file.  If neither or
    set and chunks_per_file is set it will increment the path given by the file
    number
    """
    def __init__(self, path='fileout', append=False, replace=False, chunks_per_file=None):
        self.file_count = 0
        if chunks_per_file and not isinstance(chunks_per_file, int) or chunks_per_file and chunks_per_file < 0:
            raise Exception('chunks_per_file should be an int greater than 0')
        self.chunks_per_file = chunks_per_file
        self.chunk_count = 0
        self.file = None 
        self.path = path
        Element.__init__(self)
        self.set_path(path)
    
    def set_path(self, path):
        if self.chunks_per_file and '%s' not in path:
            result = path.rpartition('.')
            if result[1] == '.':
                path = '%s%s.%s' % (result[0], '%s', result[2])
            else:
                path += '%s'
        if path.count('%s') > 1:
            raise Exception('Invalid Path, limit string interpolation count to 1')
        self.path = path
        
    def new_file(self):
        self.file_count += 1
        if self.chunks_per_file:
            path = self.path % self.file_count
        else:
            path = self.path
        file_dir = os.path.dirname(path)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        self.file = open(path, 'wb')
        
    def data_received(self, data=''):
        if not self.file:
            self.new_file()
        if data:
            self.file.write(data)
        self.chunk_count += 1
        if self.chunk_count == self.chunks_per_file:
            self.file.close()
            self.file = None
            self.chunk_count = 0
        
    def finish(self):
        if self.file:
            self.file.close()
        self.finish_connected()
        
