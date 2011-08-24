from core import Element, ApMediaError
import os

class IndexerSegment(object):
    handler = None
    file_path = ''
    deleted = False
    filename = '' 
    
    def __init__(self, handler, data, seq):
        self.handler = handler
        self.file_path = os.path.join(handler._path, handler._name_string % seq)
        file = open(self.file_path, 'wb')
        file.write(data)
        file.close()
        self.filename = handler._name_string % seq
    
    def delete(self):
        os.remove(self.file_path)
        deleted=True
    
class IndexerSegmentHandler(object):
    _name_string = None
    _path = None
    _indexer = None
    _active_limit = None
    _duration = None
    _delete_inactive_segments = None
    _segments = []
    STALE_TO_KEEP = 4 #According to the IETF you are supposed to keep the files on the system even if it is
                    #live for a length of time after it is "deleted" from the index file
    
    def __init__(self, indexer, duration, name_string='segment_num%s.ts', active_limit=3, delete_inactive_segments=True):
        self._indexer = indexer
        self._name_string = name_string
        self._duration = duration
        self._active_limit = active_limit
        self._delete_inactive_segments = delete_inactive_segments
        self._segments= []
        
    def add_segment(self, data):
        if not self._path:
            self._path = os.path.dirname(self._indexer._index_file_path)
        self._segments.append(IndexerSegment(self, data, len(self._segments)+1))
        if len(self._segments) > (self._active_limit + self.STALE_TO_KEEP) and self._delete_inactive_segments:
            self._segments[-(self._active_limit+self.STALE_TO_KEEP+1)].delete()
    
    def get_active_segments(self):
        if not self._active_limit:
            return self._segments
        if len(self._segments) > self._active_limit:
            return self._segments[-self._active_limit:]
    
    def get_current_sequence(self):
        if len(self._segments) < self._active_limit:
            return 1
        elif not self._active_limit:
            return 1
        else:
            return len(self._segments) - self._active_limit + 1
    
class Indexer(Element):
    _segment_handler = None
    _index_file_path = None
    name_string = 'segment_num%s.ts'
    target_duration = 10
    host_with_root = ''
    
    URI_TAG = '#EXTINF:%i,%s\n' #Usage should be something like {URI_TAG % (target_duration, '')} usually
    MEDIA_SEQ_TAG = '#EXT-X-MEDIA-SEQUENCE:%i\n'
    TARGET_DURATION_TAG = '#EXT-X-TARGETDURATION:%i\n'
    EXT_TAG = '#EXTM3U\n'
    END_TAG = '#EXT-X-ENDLIST\n'
    NO_CACHE_ALLOW = '#EXT-X-ALLOW-CACHE:NO\n'
    
    def __init__(self, index_file_path=None, segment_name = None, active_limit=3, delete_inactive_segments=True, target_duration=10):
        """
        Arguments:
        index_file_url - optional, something like /var/www/test_server/static/event_streams/asdflkj/index (leave off extension)
        files_directory - optional, defaults to the same directory as the index_file
        number_of_files - optional, defaults to 3 - if you set it to 0, it will not limit them
        delete_after_use - optional, default to True, sets the files to be deleted from the system after they
                                    are removed fromt he indexer
        """
        Element.__init__(self)
        #This section is to validate that we can create the index file, and then deletes the test file
        if index_file_path:
            self.set_index_file_path(index_file_path)
        else:
            self._index_file_path = None
        
        if segment_name:
            self.name_string = segment_name
        
        self._segment_handler = IndexerSegmentHandler(self, self.target_duration, name_string=self.name_string,  
                                               active_limit=active_limit, delete_inactive_segments=delete_inactive_segments)
        
        self.target_duration = target_duration
        
    def data_received(self, data):
        if not self._index_file_path:
            raise ApMediaError("index_file_path is not set.  Use set_index_file_path(path) before sending data")
        self._segment_handler.add_segment(data)
        self._update_index_file()

    def set_index_file_path(self, path):
            testfile = open(path, 'wb')
            testfile.write("Validating Index File")
            testfile.close()
            self._index_file_path = os.path.abspath(path)
            os.remove(os.path.abspath(testfile.name))        
        
    def _update_index_file(self, closed=False):
        segments = self._segment_handler.get_active_segments()
        if not segments:
            return
        sequence = self._segment_handler.get_current_sequence()
        lines = []
        lines.append(self.EXT_TAG)
        lines.append(self.TARGET_DURATION_TAG % self.target_duration)
        lines.append(self.MEDIA_SEQ_TAG % sequence)
        lines.append(self.NO_CACHE_ALLOW)
        
        for segment in segments:
            lines.append(self.URI_TAG % (self.target_duration, ''))
            lines.append(segment.filename + '\n')
        if closed:
            lines.append(self.END_TAG)
            
        index_file_m3u = open('%s.m3u' % self._index_file_path, 'wb')
        for line in lines:
            index_file_m3u.write(line)
        index_file_m3u.close()
        index_file_m3u8 = open('%s.m3u8' % self._index_file_path, 'wb')
        for line in lines:
            index_file_m3u8.write(line)
        index_file_m3u8.close()
    
    def finish(self):
        self._update_index_file(closed=True)
        self.finish_connected()
