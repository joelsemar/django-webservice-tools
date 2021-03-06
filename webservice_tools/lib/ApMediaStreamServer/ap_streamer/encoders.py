import py_ffmpeg
import py_ilbc
from core import Element

class MP3Encoder(Element):
    """
    """
    _buffer = ''
    _buffer_limit = 0
    _SAMPLE_SIZE = 1152

    def __init__(self, samples=10, finish_passes_partials=True):
        self.finish_passes_partials = finish_passes_partials
        self._buffer_limit = self._SAMPLE_SIZE * samples
        self.encoder = py_ffmpeg.mp3_encoder()
        Element.__init__(self)

    def data_received(self, data):
        self._buffer += data
        self.check_buffer()

    def check_buffer(self):
        if len(self._buffer) > self._buffer_limit:
            self.send(self.encoder.mp3_encode(self._buffer[:self._buffer_limit]))
            self._buffer = self._buffer[self._buffer_limit:]
            self.check_buffer()

    def finish(self):
        if self.finish_passes_partials:
            self.send(self.encoder.mp3_encode(self._buffer)+self.encoder.mp3_flush())
        self.finish_connected()


class ILBCDecoder(Element):
    _buffer = ''
    _buffer_limit = 0
    _SAMPLE_SIZE = 38

    def __init__(self, samples=50, finish_passes_partials=True, mode=20):
        self.finish_passes_partials = finish_passes_partials
        self.mode = mode
        self._buffer_limit = self._SAMPLE_SIZE * samples
        Element.__init__(self)

    def data_received(self, data):
        self._buffer += data
        self.check_buffer()

    def check_buffer(self):
        if len(self._buffer) > self._buffer_limit:
            self.send(py_ilbc.decode(self.mode, self._buffer[:self._buffer_limit]))
            self._buffer = self._buffer[self._buffer_limit:]
            self.check_buffer()

    def finish(self):
        if self.finish_passes_partials:
            self.send(py_ilbc.decode(self.mode, self._buffer))
        self.finish_connected()

