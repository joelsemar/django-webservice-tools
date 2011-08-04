import os
print os.getcwd()
from ap_streamer import core
from twisted.internet.protocol import Protocol, Factory
from twisted.application import internet, service
from twisted.internet import task

ONE_MB = 1024 * 1000

class ByteReceiver(Protocol):
        
    def __init__(self):
        self._indexer = core.Indexer('/tmp/audio_test/index.m3u')
        self._segmenter = core.Segmenter(5*ONE_MB, self._indexer.data_received)
        self.file_index = 1
    
    def connectionMade(self):
        print 'Connected to client.'
    
    def connectionLost(self, reason):
        print "Connection Lost"
            
    def write_to_file(self, data):
        
        with open('/tmp/audio_test/temp%s.mp3' % self.file_index, 'w') as f:
            f.write(data)
        self.file_index += 1

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

