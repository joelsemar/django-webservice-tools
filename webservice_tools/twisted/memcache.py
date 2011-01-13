# -*- coding: utf-8 -*-
"""
Interface to local memcached on the box (which Castdaemon will manage)    

$Id:memcache.py 754 2010-01-02 18:03:05Z robbyd $
@copyright:  2004-2007 Robby Dermody. 2008-Present Castdot, Inc. All Rights Reserved.
@license:    See LICENSE file for more information

"""

#############################
#MODULE DEPENDENCIES
#############################
#General deps
import uuid
from twisted.internet import defer, protocol, reactor
from twisted.python import log
from twisted.protocols import memcache

#Project-specific deps
from webservice_tools.twisted import consts, singleton


#############################
#MODULE-LEVEL VARIABLES
#############################
STORED_TOKEN_ACTIVE_PERIOD_MIN = 1 #in seconds
STORED_TOKEN_ACTIVE_PERIOD_MAX = 86400 * 5 #in seconds


#############################
#MODULE FUNCTIONALITY
#############################
class MemcacheClientFactory(protocol.ReconnectingClientFactory):
    noisy = False
    factor = 1
    maxDelay = 1

    def __init__(self, deferred):
        self.deferred = deferred
        self.proto = None #initialized in buildProtocol


    def __repr__(self):
        return "<ClientCreator factory: %r>" % (self.instance, )


    def buildProtocol(self, addr):
        self.resetDelay()
        self.proto = memcache.MemCacheProtocol()
        if self.deferred:
            reactor.callLater(0, self.deferred.callback, self.proto)
            del self.deferred
            self.deferred = None
        singleton.store('memCacheClient', self.proto)
        return self.proto


def connectToMemcached():
    """
    @return: The memcached protocol client object, or False if a connection attempt is already in progress
    """
    log.msg("%s memcache client connection..." % (singleton.get('memCacheClient', strict=False)
        and "REMAKING" or "Making",), lvl='i', ss='ss_castdaemon')

    d = defer.Deferred()
    client = MemcacheClientFactory(d)
    reactor.connectTCP("localhost", consts.MISC_MEMCACHED_PORT, client)
    return d


def storeByUUID(content, lifetime=consts.IBL_API_MEMCACHE_DEFAULT_LIFETIME):
    """
    Stores some content in the local memcache on the machine and returns a UUID-reference to that entry.
    
    @param content: The content to store (must be serializable by JSON)
    @param lifetime: (Optional.) The desired lifetime of the content in seconds. If not stated, defaults to
        L{consts_castdaemon.COMMON_STORED_TOKEN_ACTIVE_PERIOD_DEFAULT}. Valid values are
        L{consts_castdaemon.COMMON_STORED_TOKEN_ACTIVE_PERIOD_MIN} to
        L{consts_castdaemon.COMMON_STORED_TOKEN_ACTIVE_PERIOD_MAX} 
        
    @return: The UUID created for the content, or None on failure.
    """
    #generate UUID for this content
    key = str(uuid.uuid4())

    return store(key, content, lifetime)


def store(key, content, lifetime=consts.IBL_API_MEMCACHE_DEFAULT_LIFETIME):
    """    
    Stores some content in the local memcache on the machine and returns a UUID-reference to that entry.
    
    @param content: The content to store (must be serializable by JSON)
    @param lifetime: (Optional.) The desired lifetime of the content in seconds. If not stated, defaults to
        L{consts_castdaemon.COMMON_STORED_TOKEN_ACTIVE_PERIOD_DEFAULT}. Valid values are
        L{consts_castdaemon.COMMON_STORED_TOKEN_ACTIVE_PERIOD_MIN} to
        L{consts_castdaemon.COMMON_STORED_TOKEN_ACTIVE_PERIOD_MAX} 
        
    @return: The key name created (should be the same as the 'key' parameter), or None on failure.
    """
    #convert unicode strings to ascii strings
    if isinstance(key, unicode):
        key = key.encode('utf-8')
    if isinstance(content, unicode):
        content = content.encode('utf-8')

    if    lifetime < STORED_TOKEN_ACTIVE_PERIOD_MIN \
       or lifetime > STORED_TOKEN_ACTIVE_PERIOD_MAX:
        raise ValueError("lifetime parameter is out of bounds")
   
    log.msg("memcache.store: key=%s, lifetime=%s" % (key, lifetime), lvl='d2', ss='ss_iblapi_memcache')

    memcacheClient = singleton.get('memCacheClient', strict=False)
    if not memcacheClient:
        raise Exception("memCacheClient not initialized yet!")

    d = memcacheClient.set(key, content, expireTime=lifetime)
    d.addCallback(lambda result: result == True and key or None)
    d.addErrback(lambda failure: log.msg("Could not make 'set' query to memcached daemon. Failure: %s" % failure,
        lvl='e', ss='ss_iblapi_memcache'))
    return d


def retrieve(key, clearOnRetrieval=False):
    """
    Given a Key, retrieves content that was stored earlier in a local memcache.
    
    @param key: The key to get.
    @param clearOnRetrieval: Set to True to remove the data from the memcache after retrival.
    @return: The cached data, or None if not found
    """
    assert key
    #convert unicode strings to ascii strings
    if isinstance(key, unicode):
        key = key.encode('utf-8')
        
    log.msg("memcache.retrieve: key=%s, clearOnRetrieval=%s" % (key, clearOnRetrieval),
            lvl='d2', ss='ss_iblapi_memcache')

    memcacheClient = singleton.get('memCacheClient', strict=False)
    if not memcacheClient:
        raise Exception("memCacheClient not initialized yet!")
    d = memcacheClient.get(key)
    d.addCallback(_cbRetrieve, key, clearOnRetrieval, memcacheClient)
    d.addErrback(lambda failure: log.msg(u"Could not make 'get' query to memcached daemon for key '%s'. Failure: %s" % (key, failure),
        lvl='e', ss='ss_iblapi_memcache'))
    return d


def _cbRetrieve(getResult, key, clearOnRetrieval, memcacheClient):
    if getResult == (0, None):
        return None #key not found
    
    if clearOnRetrieval:
        d = memcacheClient.delete(key)
        d.addCallback(_cbRetrievePhase2, getResult, key, clearOnRetrieval)
    else:
        d = defer.succeed(None) #no delete
        d.addCallback(_cbRetrievePhase2, getResult, key, clearOnRetrieval)
    return d


def _cbRetrievePhase2(deleteResult, getResult, key, clearOnRetrieval):
    if getResult == False:
        log.msg(u"memcache.retrieve: delete FAILED for key=%s" % (key,), lvl='w', ss='ss_iblapi_memcache')
        
    return getResult[1]
