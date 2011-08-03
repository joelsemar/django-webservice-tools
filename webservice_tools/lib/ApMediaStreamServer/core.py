from exceptions import Exception
import os
from datetime import datetime
from webservice_tools import uuid

class ApMediaError(Exception):
    pass


class Element(object):
    """
    Implements data_received, and init method that sets _callback
    """
    
    class Meta:
        abstract = True
        
       
    out_callback = None
    
    out_callback_required = True
        
    def __init__(self, callback=None):
        if (self.out_callback_required and not callback):
            raise ApMediaError("Callback is required")
        self.out_callback = callback
        
    
    def data_received(self, data):
        pass
    

class Segmenter(Element):
    
    _buffer = ''
    _buffer_limit = 0
    
    
    def __init__(self, bytes_per_segment, callback=None):
        super(Element, self).__init__(callback)
        if bytes_per_segment:
            _buffer_limit = bytes_per_segment
        else:
            raise ApMediaError("Bytes per segment must be provided")
    
    def data_received(self, data):
        _buffer.append(data)
        self.check_buffer_size()
    
    
    def check_buffer_size(self):
        if len(_buffer) >= _buffer_limit:
            self.out_callback(_buffer[0:_buffer_limit])
            self._buffer = _buffer[_buffer_limit:]


class Segment(object):
    handler = None
    file_path = ''
    deleted = False
    filename = '' 
    
    def __init__(self, handler, data, seq):
        self.handler = handler
        self.file_path = os.join(handler._path, handler._name_string % seq)
        file = open(self.file_path, 'wb')
        file.write(data)
        file.close()
        self.filename = file.name
    
    def delete(self):
        os.remove(self.file_path)
        deleted=True
    
class SegmentHandler(object):
    _name_string = None
    _path = None
    _indexer = None
    _active_limit = None
    _duration = None
    _delete_inactive_segments = None
    _segments = []
    STALE_TO_KEEP = 4 #According to the IETF you are supposed to keep the files on the system even if it is
                    #live for a length of time after it is "deleted" from the index file
    
    def __init__(self, indexer, segments_path, duration, name_string='segment_num%s.ts', active_limit=3, delete_inactive_segments=True):
        self._indexer = indexer
        self._path = segments_path
        self._name_string = name_string
        self._duration = duration
        self._active_limit = active_limit
        self._delete_inactive_segments = delete_inactive_segments
        self._segments= []
        
    def add_segment(self, data):
        self._segments.append(Segment(self, data, len(self._segments)+1))
        if len(self._segments) > self._active_limit and self._delete_inactive_segments:
            self._segments[-self._active_limit+self.STALE_TO_KEEP].delete()
    
    def get_active_segments(self):
        if len(self._segments) > self._active_limit:
            return self._segments[-self._active_limit:]
    
    def get_current_sequence(self):
        if len(self._segments) < self._active_limit:
            return 1
        else:
            return len(self._segments) - self._active_limit + 1
    
class Indexer(Element):
    _segment_handler = None
    _index_file_url = ''
    name_string = 'segment_num%s'
    out_callback_required = False
    target_duration = 10
    host_with_root = ''
    
    URI_TAG = '#EXTINF:%i,%s' #Should be something like {URI_TAG % (target_duration, '')} usually
    MEDIA_SEQ_TAG = '#EXT-X-MEDIA-SEQUENCE:%i'
    TARGET_DURATION_TAG = '#EXT-X-TARGETDURATION:%i'
    EXT_TAG = '#EXTM3U'
    END_TAG = '#EXT-X-ENDLIST'
    
    def __init__(self, index_file_url, host_with_root, active_limit=3, delete_inactive_segments=True, target_duration=10):
        """
        Arguments:
        index_file_url - required - something like /var/www/test_server/static/stream5/index_
        files_directory - optional, defaults to the same directory as the index_file
        number_of_files - optional, defaults to 3 - if you set it to 0, it will not limit them
        delete_after_use - optional, default to True, sets the files to be deleted from the system after they
                                    are removed fromt he indexer
        """
        super(Element, self).__init__(callback)
        if not index_file_url:
            raise ApMediaError("index_file_url must be provided")
        if not host_with_root:
            raise ApMediaError("host_with_root (ie www.example.com/segments/event35/) is required")
        #This section is to validate that we can create the index file, and then deletes the test file
        try:
            testfile = open(index_file_url, 'wb')
            testfile.write("Validating Index File")
            testfile.close()
            os.remove(os.path.abspath(testfile.name))
            self._index_file_url = index_file_url
        except Exception as (e, str):
            raise e("File Creation test failed at: %s" % index_file_url)

        segments_path = os.path.abspath(os.path.dirname(_index_file.name))
        
        self._segment_handler = SegmentHandler(self, segments_path, self.target_duration, name_string=self.name_string,  
                                               active_limit=active_limit, delete_inactive_segments=delete_inactive_segments)
        
        self.target_duration = target_duration
        self.host_with_root = host_with_root
        
    def data_received(self, data):
        self._segment_handler.add_segment(data)
        self.update_index_file()
        
    def update_index_file(self):
        segments = self._segment_handler.get_active_segments()
        if not segments:
            return
        sequence = self._segment_handler.get_current_sequence()
        index_file = open(self._index_file_url, 'wb')
        self._write_header(index_file, sequence)
        for segment in segments:
            index_file.writeline(self.URI_TAG % (self.target_duration, ''))
            index_file.writeline('%s%s' % (self.host_with_root, segment.name))
        
    def _write_header(self, index_file, seq):
        index_file.writeline(EXT_TAG)
        index_file.writeline(self.TARGET_DURATION_TAG % self.target_duration)
        index_file.writeline(self.MEDIA_SEQ_TAG % seq)
        
        
