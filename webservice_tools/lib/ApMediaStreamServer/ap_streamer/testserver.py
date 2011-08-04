import os
print os.getcwd()
from ap_streamer import core
from twisted.internet.protocol import Protocol, Factory
from twisted.application import internet, service
from twisted.internet import task

ONE_MB = 1024 * 1000

class ByteReceiver(Protocol):
        
    def __init__(self):
        self._indexer = core.Indexer('/var/www/web/audio_test/index.m3u', active_limit=0)
        self._segmenter = core.Segmenter(50 * 38, self._indexer.data_received, target_duration=1, delete_inactive_segments=False)
        self.file_index = 1
    
    def connectionMade(self):
        print 'Connected to client.'
    
    def connectionLost(self, reason):
        print "Connection Lost"
    
    def dataReceived(self, data):
        """
         Protocol.dataReceived.
        Translates bytes into lines, and calls lineReceived (or
        rawDataReceived, depending on mode.)
        """
        self._segmenter.data_received(data)
        
class ClientFactory(Factory):
    protocol = ByteReceiver
    
    
# application object
application = service.Application("Demo application")
internet.TCPServer(11921, ClientFactory()).setServiceParent(application)

