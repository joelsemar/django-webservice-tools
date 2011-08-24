import py_ffmpeg
from core import Element

class MP3Encoder(Element):    
    """
    """
    _buffer = ''
    _buffer_limit = 0
    _SAMPLE_SIZE = 1152
    
    def __init__(self, samples=None, finish_passes_partials=True):
        self.finish_passes_partials = finish_passes_partials
        if not samples:
            raise ApMediaError("Number of samples must be provided")
        self._buffer_limit = self._SAMPLE_SIZE * samples 
        
    def data_received(self, data):
        self._buffer += data
        self.check_buffer()
    
    def check_buffer(self):
        if len(self._buffer) > self._buffer_limit:
            self.send(self._buffer[:self._buffer_limit])
            self._buffer = self._buffer[self._buffer_limit:]
            self.check_buffer()
            
    def finish(self):
        if self.finish_passes_partials:
            self.send(self._buffer)
        self.finish_connected()

    