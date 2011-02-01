# -*- coding: utf-8 -*-
"""
Functions for accessing and manipulating the database

$Id:dbutil.py 1145 2010-03-17 01:54:07Z robbyd $
@copyright:  2004-2007 Robby Dermody. 2008-Present Castdot, Inc. All Rights Reserved.
@license:    See LICENSE file for more information
"""

#############################
#MODULE DEPENDENCIES
#############################
#General deps
import os
import sys
import datetime
import time
import hashlib
import Queue
import MySQLdb
import simplejson
import base64
from twisted.enterprise import adbapi
from twisted.internet import defer, reactor, protocol, task, threads
from twisted.python import log

#Project specific deps
#from castdot.shared import consts_shared, sharedstrutil, sharedutil, singleton
from webservice_tools.twisted import config, consts, errorutil, memcache, twistedstrutil, twistedutil, singleton


#############################
#MODULE-LEVEL VARIABLES
#############################
CONNECTION_POOL_RETRY_DECREASE_PERIOD = 10 #how many seconds between decrementing the counter
CONNECTION_POOL_RETRY_DECREASE_RATE_PER_PERIOD = 5 #counter decreased by this amount per period
CONNECTION_POOL_HIGH_WATER_MARK = 100 #high water mark of this connection pool retry counter before we trigger a fatal error
PERIODIC_CONNECTION_PING_INTERVAL = 4400 #in seconds, 4400 = 1 hour
PERIODIC_TRY_EMPTY_QUERY_BACKLOG_INTERVAL = 2 #in seconds (should normally stay as 1 or 2)
PERIODIC_CHECK_FOR_MAX_CONNECTIVITY_OUTAGE_INTERVAL = 1 #in seconds (this should stay as 1)
QUERY_BACKLOG_MAXSIZE = 200 #cache up at most this many queries against a disconnected connection pool before
# throwing a fatal error (queue max reached)
QUERY_BACKLOG_MAX_CONN_DOWN_TIME = 60 #in seconds
EXECUTE_ALREADY_QUEUED_RETURNDATA = "DBEXECUTE-BACKLOG-ALREADYQUEUED"


#############################
#MODULE FUNCTIONALITY
#############################
def _isMySQLServerConnDownErrorMessage(errorMessage):
    errorMessages = ("mysql server has gone away", "lost connection to mysql server during query",
        "can't connect to local mysql server through socket", "can't connect to mysql server on")
    return any([x in str(errorMessage).lower() for x in errorMessages])


def _produceCacheHashKey(queryStringOrProcName, argList, fetch):
    if isinstance(queryStringOrProcName, str):
        #decode into a unicode string
        queryStringOrProcName = queryStringOrProcName.decode('utf-8')
    #decode string args as well
    for i in xrange(len(argList)):
        if isinstance(argList[i], str):
            argList[i] = argList[i].decode('utf-8')
    
    cacheHashKey = argList and (unicode(queryStringOrProcName) + u'|' + unicode(fetch)
        + u'|'.join([unicode(x) for x in argList])) or unicode(queryStringOrProcName)
    cacheHashKey = hashlib.md5(cacheHashKey.encode('utf-8')).hexdigest()
    return cacheHashKey


def _getBacklogEntryLoggingHash(backlogItem):
    if backlogItem['callType'] == 'callProc':
        return _produceCacheHashKey(backlogItem['procName'], backlogItem['inArgList'], backlogItem['fetch'])
    elif backlogItem['callType'] == 'execute':
        return _produceCacheHashKey(backlogItem['queryString'], backlogItem['argList'], backlogItem['fetch'])




class QuietConnection(adbapi.Connection):
    """A slightly modified version of adbapi.Connection
    """

    def rollback(self):
        """OVERRIDDEN FROM Twisted 8.2.0 code -- Modified to not bitch when a rollback fails
        """
        if not self._pool.reconnect:
            self._connection.rollback()
            return

        try:
            self._connection.rollback()
            curs = self._connection.cursor()
            curs.execute(self._pool.good_sql)
            curs.close()
            self._connection.commit()
            return
        except:
            #log.err(None, "Rollback failed")
            pass

        self._pool.disconnect(self._connection)

        if self._pool.noisy:
            log.msg(u"Connection lost.")

        raise adbapi.ConnectionLost()




class BackloggingConnectionPool(adbapi.ConnectionPool):
    """A frontend to twisted's ConnectionPool so that we try to reconnect to mysql if/when the connection goes
    down.
    
    Custom castdot enhancements include the ability to tolerate limited loss of DB connectivity. In the case
    one or more connections in the pool loose connectivity, queries issued to the connection pool will be
    queued up (backlogged). Once connectivity is established, queries will be reissued to the database. All
    functionality is maintained and normally no exceptions will occur as the deferred that execute/callProc
    returns will actually be fired once the query is finally successfully issued to the DB (i.e. after the
    connectivity is re-established).
    
    This means that what one will see when DB connectivity is lost is that
    the castdaemon basically slows to a crawl as there is an accumulation of deferred operations that are
    essentially waiting for the DB connection to be re-established so they can complete. Once connectivity
    is re-established, the castdaemon will "catch-up" and will resume normal operations. Given the extremely
    disruptive nature of DB connectivity errors, this method of action is basically the best that we can get,
    and is definitely a better alternative to blindly throwing exceptions (as these can disable random code-execution
    paths of the castdaemon in a way that is hard to detect), or throwing a fatal error (which will just
    stop everything from working, even for very short and temporary DB connectivity "hiccups").
    
    Important implementation notes:
    - The current implementation of this does NOT guarantee that queries will be re-executed in
    the order in which they were queued. The current implementation instead only attempts a "best effort"
    attempt at keeping query order. This should not be an issue due to the fact that in-order query execution
    should be maintained where it really matters via deferred chaining elsewhere in the castdaemon.
    
    - A fatal error is thrown when the query backlog exceeds a maximum size (QUERY_BACKLOG_MAXSIZE entries),
    and/or DB connectivity is down for over some period of time (QUERY_BACKLOG_MAX_CONN_DOWN_TIME seconds).
    
    - Query backlogging is NOT supported for queries made through L{runInteraction}, L{runWithConnection},
    and L{executeOnCursor}.
    """
    connectionFactory = QuietConnection
    
    def __init__(self, *args, **kwargs):
        assert 'poolName' in kwargs 
        self._poolName = kwargs['poolName']
        del kwargs['poolName']
        
        if not kwargs['cp_reconnect']:
            raise Exception("the 'reconnect' argument must be set to True for reconnect functionality to work."
                " Aborting initialization!")
        
        #self._connPoolRetryAttemptCounter = 0
        #self._decreaseRetryAttemptCounterLoop = None
        self._periodicConnPingLoop = None
        #self._queryBacklog = Queue.Queue(QUERY_BACKLOG_MAXSIZE)
        self._queryBacklog = []
        self._connectivityDownSince = None
        self._connectivityLastRestored = None
        
        #init parent
        adbapi.ConnectionPool.__init__(self, *args, **kwargs)

        self._periodicConnPingLoop = task.LoopingCall(self._periodicConnPing)
        dLoop = self._periodicConnPingLoop.start(PERIODIC_CONNECTION_PING_INTERVAL, now=False)
        dLoop.addErrback(log.err) #don't put a callback on this deferred, however

        self._periodicTryEmptyQueryBacklogLoop = task.LoopingCall(self._periodicTryEmptyQueryBacklog)
        dLoop = self._periodicTryEmptyQueryBacklogLoop.start(PERIODIC_TRY_EMPTY_QUERY_BACKLOG_INTERVAL, now=False)
        dLoop.addErrback(log.err) #don't put a callback on this deferred, however

        self._periodicCheckForMaxConnectivityOutageLoop = task.LoopingCall(self._periodicCheckForMaxConnectivityOutage)
        dLoop = self._periodicCheckForMaxConnectivityOutageLoop.start(PERIODIC_CHECK_FOR_MAX_CONNECTIVITY_OUTAGE_INTERVAL, now=False)
        dLoop.addErrback(log.err) #don't put a callback on this deferred, however


    def _periodicConnPing(self):
        """
        Pings across all connections on the database. Used to keep the connectivity alive and prevent idle
        timeouts on the MySQL server.
        """
        if singleton.get('castdaemon', strict=False) and (singleton.get('castdaemon').isShuttingDown() or errorutil.checkIfFatalErrorOccurred()):
            return
         
        cannotPingOnConns = []
        firstExceptionValue = None
        for conn in self.connections.values():
            try:
                conn.ping()
            except MySQLdb.OperationalError:
                excType, excValue, excTraceback = sys.exc_info()
                
                #try to close this connection
                try:
                    self._close(conn)
                except MySQLdb.ProgrammingError: #closing a closed connection
                    #connection is already closed, don't include it in our list of bad connections we had
                    pass

                cannotPingOnConns.append(conn)
                if not firstExceptionValue:
                    firstExceptionValue = excValue
        
        if len(cannotPingOnConns):    
            log.msg(u"Could not ping MySQL server for pool \"%s\" on %i of %i pool connections: %s. Reset these connections..." % (
                self._poolName, len(cannotPingOnConns), len(self.connections.values()), firstExceptionValue),
            lvl='w', ss='ss_db')

    
    def _periodicTryEmptyQueryBacklog(self):
        """Will periodically check if the query backlog has any entries in it, and if so, try to issue those
        pending queries against the DB.
        """ 
        if singleton.get('castdaemon', strict=False) and (singleton.get('castdaemon').isShuttingDown() or errorutil.checkIfFatalErrorOccurred()):
            return
         
        if not self.getQueryBacklogSize():
            return
        
        #print "PERIODIC trying to empty backlog, size is", self.getQueryBacklogSize() 
        d = self._emptyBacklog()
        return d
    
    
    def _periodicCheckForMaxConnectivityOutage(self):
        if     self._connectivityDownSince \
           and self._connectivityDownSince + QUERY_BACKLOG_MAX_CONN_DOWN_TIME < time.time():
            errorutil.triggerFatalError(
                "Loss of DB connectivity for pool \"%s\" has exceeded max allowable length of %i seconds. Exiting!"
                % (self._poolName, QUERY_BACKLOG_MAX_CONN_DOWN_TIME))
            

    def getWhenConnectivityDownSince(self):
        """Returns a timestamp of when the current instance of loss of DB connectivity for this ConnectionPool
        happened.
         
        @return: A UNIX timestamp, or None if connectivity is currently up.
        """
        return self._connectivityDownSince
    
    
    def getWhenConnectivityLastRestored(self):
        """Returns a timestamp of when connectivity was last fully restored on this server for the current run.
         
        @return: A UNIX timestamp, or None if connectivity has not yet had to be restored on this server for
        the current run.
        """
        return self._connectivityLastRestored
    
    
    def _addToQueryBacklog(self, item):
        """
        Adds a query backlog item to the backlog queue
        
        @return: Return a deferred yielding true if the adding was successful, or false if not.
        """
        #signify last DB sync lost
        if not self._connectivityDownSince:
            self._connectivityDownSince = time.time()
        
        if len(self._queryBacklog) >= QUERY_BACKLOG_MAXSIZE:
            #connection has been dead for too long, die
            errorutil.triggerFatalError("Query backlog for pool \"%s\" would overflow (DB down for too long). Exiting!"
                % (self._poolName,))
            return None
        
        self._queryBacklog.append(item)
        return True
    
    
    def _removeFromQueryBacklog(self):
        """Gets an item from the query backlog.
        
        @return: The item received, or None if there was no item to get.
        """
        if not self._queryBacklog:
            return None

        item = self._queryBacklog.pop(0)
        return item
    
    
    def _peekAtQueryBacklogHead(self):
        if not len(self._queryBacklog):
            return None
        
        return self._queryBacklog[0]
    
    
    def getQueryBacklogSize(self):
        #return self._queryBacklog.qsize()
        return len(self._queryBacklog)
        
    
    def connect(self):
        conn = adbapi.ConnectionPool.connect(self)
        #CASTDOT-CUSTOM: call _emptyBacklog
        threads.blockingCallFromThread(reactor, self._emptyBacklog)
        return conn


    def _close(self, conn):
        """OVERRIDDEN FROM Twisted 8.2.0 code -- Modified to not bitch about closing connections that
        are already closed.
        """
        if self.noisy:
            log.msg('adbapi closing: %s' % (self.dbapiName,))
 
        try:
            conn.close()
        except MySQLdb.ProgrammingError: #closing a closed connection
            pass
        except:
            log.err(None, "Connection close failed")
 
    
    def _runInteraction(self, interaction, *args, **kw):
        """See http://www.gelens.org/2009/09/13/twisted-connectionpool-revisited/"""
        try:
            return adbapi.ConnectionPool._runInteraction(self, interaction, *args, **kw)
        except MySQLdb.OperationalError, e:
            if e[0] not in (2006, 2013):
                raise
            log.msg(u"Got error code %s: \"%s\", retrying operation (pool \"%s\")"
                % (e[0], e[1], self._poolName,), lvl='d2', ss='ss_db')                
            conn = self.connections.get(self.threadID())
            self.disconnect(conn)
            # try the interaction again
            return adbapi.ConnectionPool._runInteraction(self, interaction, *args, **kw)
        except adbapi.ConnectionLost, e:
            log.msg(u"Got Connection lost error, retrying operation (pool \"%s\")"
                % (self._poolName,), lvl='d2', ss='ss_db')                
            conn = self.connections.get(self.threadID())
            self.disconnect(conn)
            # try the interaction again
            return adbapi.ConnectionPool._runInteraction(self, interaction, *args, **kw)


    def _emptyBacklog(self):
        """Called when:
        1. a new connection is established/reestablished (as the cp_openfun arg to ConnectionPool); or
        2. periodically by the connection pool, if its query backlog is not empty
        
        If we have any entries in our connection backlog, empty them now.
        """
        backlogPresent = False
        d = defer.succeed(True)
        
        while True: 
            #backlogItem = self._peekAtQueryBacklogHead()
            backlogItem = self._removeFromQueryBacklog()
            if not backlogItem:
                #empty backlog
                break

            #otherwise we have a backlog item to process
            backlogPresent = True
            assert backlogItem['callType'] in ('callProc', 'execute')
            if backlogItem['callType'] == 'callProc':
                d.addCallback(lambda result, backlogItem=backlogItem: callProc(backlogItem['procName'],
                    backlogItem['inArgList'], backlogItem['fetch'], backlogItem['connID'], backlogItem['useCache'],
                    backlogItem['cacheExpireTime'], backlogItem['printQuery'], _alreadyInBacklog=True))
            elif backlogItem['callType'] == 'execute':
                d.addCallback(lambda result, backlogItem=backlogItem: execute(backlogItem['queryString'],
                    backlogItem['argList'], backlogItem['fetch'], backlogItem['connID'], backlogItem['useCache'],
                    backlogItem['cacheExpireTime'], backlogItem['printQuery'], _alreadyInBacklog=True))
                d.addCallback(self._cbEmptyBacklog_perEntry, backlogItem, self.getQueryBacklogSize())
        d.addCallback(self._cbEmptyBacklog, backlogPresent)
        return d


    def _cbEmptyBacklog_perEntry(self, result, backlogItem, newBacklogSize):
        if result == EXECUTE_ALREADY_QUEUED_RETURNDATA:
            #we couldn't end up actually issuing the query/proc, don't remove it from the backlog
            if backlogItem['callType'] == 'callProc':
                log.msg(u"Couldn't remove query with MD5 of \"%s\" as connection still not back up..."
                    % (_getBacklogEntryLoggingHash(backlogItem),), lvl='d2', ss='ss_db')
            elif backlogItem['callType'] == 'execute':
                log.msg(u"Couldn't remove proc with MD5 of \"%s\" as connection still not back up..."
                    % (_getBacklogEntryLoggingHash(backlogItem),), lvl='d2', ss='ss_db')
            self._addToQueryBacklog(backlogItem)
            return

        if backlogItem['callType'] == 'callProc':
            log.msg(u"Connectivity re-established: Executed proc (MD5: %s): \"%s\". New backlog length: %i"
                % (_getBacklogEntryLoggingHash(backlogItem), backlogItem['procName'], newBacklogSize),
                lvl='i', ss='ss_db')
        elif backlogItem['callType'] == 'execute':
            log.msg(u"Connectivity re-established: Executed query (MD5: %s): \"%s\". New backlog length: %i"
                % (_getBacklogEntryLoggingHash(backlogItem),
                   sharedstrutil.truncate(sharedstrutil.removeMultipleSpacesFromString(
                   backlogItem['queryString']), 80).strip(), newBacklogSize), lvl='i', ss='ss_db')
        
        #the query has completed so fire off the dRequestCompleted deferred...
        #backlogItem['dRequestCompleted'].chainDeferred(d)
        backlogItem['dRequestCompleted'].callback(result)

    
    def _cbEmptyBacklog(self, unused, backlogPresent):
        if backlogPresent and self.getQueryBacklogSize() == 0:
            #NOTE that this condition may trigger two times in quick succession for any given conn pool 
            self._connectivityDownSince = None #connectivity no longer down
            self._connectivityLastRestored = time.time()
            
            #as we successfully cleared a backlog, purposefully refresh our server stats now just to be safe (and to reduce
            # the chance the the AC sees us as dead) (or if this is the case, to properly realize it)
            if self._poolName == 'dbMetastore':
                log.msg(u"dbMetastore connectivity restored, doing full server refresh as a backlog was present...", lvl='i', ss='ss_db')
                singleton.get('core').updateServerStats()
                singleton.get('core').doRefresh(doFullRefresh=False)
        

        

def fetchResultRowToDict(txn, row):
    if row is None:
        return None
    cols = [ d[0] for d in txn.description ]
    result = dict(zip(cols, row))
    return result         


def fetchResultRowsToDict(txn, rows):
    if rows is None:
        return None
    cols = [ d[0] for d in txn.description ]
    results = [dict(zip(cols, row)) for row in rows ]
    return results  


def establishConnection(connID, hostname, port, username,
password, database, minPoolCons, maxPoolCons, sslEnabled=False, sslCACert='', useServerCursor=False,
dbProxySecHosts=None):
    """I establish a connection to either:
        - A mySQL SQL server using twisted's ADBAPI connection pool semantics.
        - A dbproxy server using twisted perspective broker (PB).
        
    @param connectType: One of the following:
        - 'direct': Establish a connection to a mySQL SQL server using twisted's ADBAPI connection pool semantics.
        - 'dbproxy': Establish a connection to a dbproxy server using twisted perspective broker (PB).
    
    @param connID: A key to use that uniquely identifies this connection (pool). It is stored
    using our singleton interface, so if you make a pool with an ID of 'dbMyPool', you can get that
    connection object by using "singleton.get('dbMyPool'). Let's use the convention where every db pool
    ID must start with 'db' to avoid clashes with other objects stored in the singleton.
    @type connID: str
    
    @param hostname: The hostname or IP address of the database server. 
    @type hostname: str
    
    @param username: The username used to connect to the database. 
    @type username: str
    
    @param port: The port used to connect to the database. 
    @type port: int

    @param password: The password used to connect to the database. 
    @type password: str
    
    @param database: The default database name that we USE once connected. 
    @type database: str

    @param minPoolCons: The minimum number of connections to keep open to the database as part of the
    connection pool. 
    @type minPoolCons: int

    @param maxPoolCons: The maximum number of connections to keep open to the database as part of the
    connection pool. 
    @type maxPoolCons: int
    """
    assert isinstance(connID, basestring) and len(connID) >= 2 and connID[0:2] == 'db'
    assert hostname and isinstance(hostname, basestring)
    assert port and isinstance(port, int)
    assert minPoolCons and isinstance(minPoolCons, int)
    assert maxPoolCons and isinstance(maxPoolCons, int)
    assert (sslEnabled and sslCACert) or not sslEnabled
    
    d = None
    
        
    assert database and isinstance(database, basestring)
    assert username and isinstance(username, basestring)
    assert password and isinstance(password, basestring)
    
    #connect directly to mysql database
    #for possible SSL support
    sslDict = {
        'ca': sslCACert,
        'capath': None,
        'key': None,
        'cert': None,
        'cipher': None,
    }
    
    cursorClassDict = {}
    if useServerCursor:
        from MySQLdb.cursors import SSCursor
        cursorClassDict['cursorclass'] = SSCursor
    #try:
    connPool = adbapi.ConnectionPool("pyPgSQL.PgSQL",
    #connPool = BackloggingConnectionPool("pyPgSQL.PgSQL",
        database=database,user=username, password=password,)
        #host=hostname, port=port, user=username, passwd=password,
        #db=database, cp_min=minPoolCons, cp_max=maxPoolCons)
        #use_unicode=True, charset='utf8', ssl=sslEnabled and sslDict or None,
        #cp_noisy=False,
        #cp_reconnect=True, poolName=connID,
        #**cursorClassDict)
    #except:
       #errorutil.triggerFatalError("Could not connect to database for pool \"%s\"" % connID)
        
    d = defer.succeed(True)
    singleton.store(connID + 'Type', 'direct')
    singleton.store(connID, connPool)
    return d
    
    
def terminateConnection(connID):
    """I close the connection pool with the given ID
    
    @param connID: The ID of the pool to close
    @type connID: str
    """
    #Database connection is already closed by this point in twisted 2.x - what about PB? (closed automatically)
    singleton.remove(connID, errorLevelIfNonExistent='n')


def callProc(procName, inArgList=(), fetch='N', connID='dbMetastore', useCache=False,
cacheExpireTime=consts.MEMCACHED_DEFAULT_EXPIRE_PERIOD, printQuery=False):
    """
    I execute a stored procedure on the database, and optionally trigger a callback function to handle
    the results.
    
    How it works:
        - Some other code calls CallProc()
        - processingCbFunc called in database pool thread context to query the database, via runIteration
        - runInteraction returns requested data as a deferred

    @param procName: The name of the stored procedure to call
    @type procName: str
    
    @param inArgList: The arguments to the stored procedure. INOUT args not supported currently.
    @type inArgList: tuple
    
    @param fetch: How to fetch the data, one of the following:
        - N: Don't fetch anything back
        - o: Fetch one (as a tuple)
        - om: Fetch one as a map
        - a: Fetch All (as a tuple)
        - am: Fetch All as a map
    @type fetch: str
    
    @param printQuery: Set to True to print the query to be executed. False by default.    
    
    @return: A deferred that is triggered when the database operation is complete
    """
    assert isinstance(procName, basestring)
    assert isinstance(inArgList, tuple)
    assert fetch in ('N', 'o', 'om', 'a', 'am')
    assert singleton.get(connID + 'Type') in ('direct', 'dbproxy')
    
    #decode any bytestrings passed in as querystring or within arglist into unicode strings
    if isinstance(procName, str):
        #decode into a unicode string
        procName = procName.decode('utf-8')
    #decode string args as well
    for i in xrange(len(inArgList)):
        if isinstance(inArgList[i], str):
            inArgList[i] = inArgList[i].decode('utf-8')
    
    log.msg(u"Processing stored proc call: \"%s\"; InArgs: %s" % (procName, inArgList,),
            lvl=printQuery and 'a' or 'd2', ss='ss_db')

    if     singleton.get('core', strict=False) \
       and singleton.get('core').getPlatformSetting('castdaemon_dbcache_interval', strict=False) == 0:
        #we are running as the castdaemon and caching is disabled
        useCache = False #override any True value

    #first, see if we are to use the memcache and try to pull the item from it if so
    if useCache:
        #use the query string itself, along with the args list as the hash key, and the fetch mode
        cacheHashKey = _produceCacheHashKey(procName, inArgList, fetch) 
        d = memcache.retrieve(cacheHashKey)
        d.addCallback(_cbCallProc, procName, inArgList, fetch, connID, useCache, cacheExpireTime, printQuery,
                      cacheHashKey)
    else:
        cacheHashKey = ""
        d = defer.succeed(None)
        d.addCallback(_cbCallProc, procName, inArgList, fetch, connID, useCache, cacheExpireTime, printQuery,
                      cacheHashKey)
    return d


def _cbCallProc(cacheValue, procName, inArgList, fetch, connID, useCache, cacheExpireTime, printQuery, cacheHashKey):
    if cacheHashKey and cacheValue:
        #useCache set to true and we found something in the cache
        #serialize it out from JSON
        try:
            cacheValue = simplejson.loads(cacheValue, encoding='utf-8')
            return cacheValue
        except:
            log.msg(u"Could not load previously stored database results from memcached; could not unserialize from JSON for proc: \"%s\". InArgs: \"%s\""
                    % (procName, inArgList), lvl='w', ss='ss_db')
    
    #otherwise we're not caching or did not find anything in the memcache...call the proc
    if singleton.get(connID + 'Type') == 'direct':
        d = singleton.get(connID).runInteraction(_directProcessCallProc, procName, inArgList, fetch, connID, useCache,
            cacheExpireTime, cacheHashKey, printQuery)
        d.addErrback(_directProcessCallProc_onError, procName, inArgList, fetch, connID, useCache,
            cacheExpireTime, cacheHashKey, printQuery)
        return d
    else: #dbproxy
        return singleton.get(connID).callProc(procName, inArgList, fetch, connID, useCache,
            cacheExpireTime, cacheHashKey)
    

def _directProcessCallProc(txn, procName, inArgList, fetch, connID, useCache, cacheExpireTime, cacheHashKey,
printQuery):
    try:
        #no out arguments
        if fetch in ('a', 'am', 'N'):
            txn.execute("CALL %s(%s);" % (procName, ", ".join(["'%s'" % arg for arg in inArgList])))
            if fetch == 'o':
                results = txn.fetchone()
            elif fetch == 'om':
                row = txn.fetchone()
                results = fetchResultRowToDict(txn, row)
            elif fetch == 'a':
                results = txn.fetchall()
            elif fetch == 'am':
                rows = txn.fetchall()
                results = fetchResultRowToDict(txn, rows)
    except:
        raise

    if useCache:
        #cache this result in memory
        assert cacheHashKey
        
        try:
            jsonResults = simplejson.dumps(results)
        except:
            #do not store in the memcache
            log.msg(u"Could not store database results in memcached; could not serialize into JSON for proc: \"%s\". InArgs: \"%s\""
                    % (procName, inArgList), lvl='w', ss='ss_db')
            return results

        #if we are running this code in the castdaemon, override the cache period with the DB-based setting
        if     cacheExpireTime == consts.MEMCACHED_DEFAULT_EXPIRE_PERIOD \
           and singleton.get('core', strict=False):
            cacheExpireTime = singleton.get('core').getPlatformSetting('castdaemon_dbcache_interval', strict=False) \
                or consts.MEMCACHED_DEFAULT_EXPIRE_PERIOD
        
        threads.blockingCallFromThread(reactor, memcache.store, cacheHashKey, jsonResults, lifetime=cacheExpireTime)
    return results


def _directProcessCallProc_onError(failure, procName, inArgList, fetch, connID, useCache,
cacheExpireTime, cacheHashKey, printQuery, _alreadyInBacklog):
    if failure.check(MySQLdb.ProgrammingError) or failure.check(TypeError):
        log.msg(u"Database query failure. Error: %s. Failed proc was: %s; Args: (%s)"
            % (failure.getErrorMessage(), procName, ', '.join([x for x in inArgList]),), lvl='e', ss='ss_db')
        failure.raiseException() #invalid syntax error
    elif failure.check(MySQLdb.OperationalError):
        if singleton.get('castdaemon', strict=False) and (singleton.get('castdaemon').isShuttingDown() or errorutil.checkIfFatalErrorOccurred()):
            #we shouldn't try to queue queries when the server is going down (as this may hold up the shutdown
            # process)
            failure.raiseException()
        
        if     _isMySQLServerConnDownErrorMessage(failure.getErrorMessage()) \
           and not _alreadyInBacklog:
            #currently not connected, queue up the request to be run when the connection is restored
            dRequestCompleted = defer.Deferred() #will be fired when the query is finally issued against the DB
            backlogItem = {'callType': 'callProc', 'procName': procName, 'inArgList': inArgList,
                'fetch': fetch, 'connID': connID, 'useCache': useCache,
                'cacheExpireTime': cacheExpireTime, 'cacheHashKey': cacheHashKey, 'printQuery': printQuery,
                'dRequestCompleted': dRequestCompleted, }

            log.msg(u"Connectivity failure: Queuing proc (MD5: %s): \"%s\". New backlog length: %i"
                % (_getBacklogEntryLoggingHash(backlogItem), procName,
                   singleton.get(connID).getQueryBacklogSize() + 1), lvl='i', ss='ss_db')

            singleton.get(connID)._addToQueryBacklog(backlogItem)
            return backlogItem['dRequestCompleted']
        elif _isMySQLServerConnDownErrorMessage(failure.getErrorMessage()) and _alreadyInBacklog:
            #don't insert the entry in to the backlog again as it's already there
            #print "dbExecute: CONNECTION STILL DOWN!"
            return EXECUTE_ALREADY_QUEUED_RETURNDATA
        else:
            log.msg(u"Unknown database operational error. Error: %s. Failed proc was: %s; Args: (%s)"
                % (failure.getErrorMessage(), procName,
                    ', '.join([x for x in inArgList]),), lvl='e', ss='ss_db')
            failure.raiseException()


def execute(queryString, argList=tuple(), fetch='N', connID='dbMetastore', useCache=False,
cacheExpireTime=consts.MEMCACHED_DEFAULT_EXPIRE_PERIOD, printQuery=False,
_alreadyInBacklog=False, many=False):
    """
    Executes a SQL statement on the database
    
    @param useCache: Set to True to use to cache the results of the query in memcached, or
    if the results are already cached in memcached, the cached version will be returned instead of having to
    make a query to the DB again.
    @param cacheExpireTime: The length of time that the result is valid in the memcache for (in seconds).
    This value is only used if memCacheKey is set to True.
    
    @see: The arguments for L{callProc}
    
    @param fetch: Same as the arguments for L{callProc}, with the addition of:
        - 'lid': Return the last insert ID (not in a tuple or list)
        
    @return: A deferred that yields the result of the query, or the data "DBEXECUTE-BACKLOG-ALREADYQUEUED" if we were executing
    a backlogged query (_alreadyInBacklog=True) and the DB was still downed (meaning it could still not be
    successfully processed)

    """
    assert queryString and len(queryString) >= 6
    assert fetch in ('N', 'o', 'om', 'a', 'am', 'lid')
    assert singleton.get(connID + 'Type') in ('direct', 'dbproxy')
    
    #decode any bytestrings passed in as querystring or within arglist into unicode strings
    #if isinstance(queryString, str):
        #decode into a unicode string
    #    queryString = queryString.decode('utf-8')
    #decode string args as well
    #for i in xrange(len(argList)):
    #    if isinstance(argList[i], str):
    #        argList[i] = argList[i].decode('utf-8')
    
    #some sanity checks
    if useCache and queryString.lstrip()[0:6].upper() != 'SELECT':
        raise Exception("useCache can only be set for SELECT queries. Failed query was: %s" % queryString)

    #make sure argList ends up being a tuple
    if not isinstance(argList, tuple):
        argList = tuple(argList)
    
    log.msg(u"Executing query: \"%s\"; Args: %s" % (queryString, argList,),
            lvl=printQuery and 'a' or 'd2', ss='ss_db')

    if     singleton.get('core', strict=False) \
       and singleton.get('core').getPlatformSetting('castdaemon_dbcache_interval', strict=False) == 0:
        #we are running as the castdaemon and caching is disabled
        useCache = False #override any True value

    #first, see if we are to use the memcache and try to pull the item from it if so
    if useCache:
        #use the query string itself, along with the args list as the hash key
        cacheHashKey = _produceCacheHashKey(queryString, argList, fetch)
        d = memcache.retrieve(cacheHashKey)
        d.addCallback(_cbExecute, queryString, argList, fetch, connID, useCache, cacheExpireTime, printQuery,
                      cacheHashKey, _alreadyInBacklog, many)
    else:
        cacheHashKey = ""
        d = defer.succeed(None)
        d.addCallback(_cbExecute, queryString, argList, fetch, connID, useCache, cacheExpireTime, printQuery,
                      cacheHashKey, _alreadyInBacklog, many)
    return d


def _cbExecute(cacheValue, queryString, argList, fetch, connID, useCache, cacheExpireTime, printQuery, cacheHashKey,
_alreadyInBacklog, many):
    if cacheHashKey and cacheValue:
        #useCache set to true and we found something in the cache
        #serialize it out from JSON
        try:
            cacheValue = simplejson.loads(cacheValue, encoding='utf-8')
            return cacheValue
        except:
            log.msg(u"Could not load previously stored database results from memcached; could not unserialize from JSON for query: \"%s\". Args: \"%s\""
                    % (queryString, argList), lvl='w', ss='ss_db')

    #otherwise we're not caching or did not find anything in the memcache...make the query
    if singleton.get(connID + 'Type') == 'direct':
        d = singleton.get(connID).runInteraction(_directProcessExecute, queryString, argList, fetch, connID, useCache,
            cacheExpireTime, cacheHashKey, printQuery, many)
        d.addErrback(_directProcessExecute_onError, queryString, argList, fetch, connID, useCache,
            cacheExpireTime, cacheHashKey, printQuery, _alreadyInBacklog)
        return d
    else: #dbproxy
        return singleton.get(connID).execute(queryString, argList, fetch, connID, useCache,
            cacheExpireTime, cacheHashKey)


def _directProcessExecute(txn, queryString, argList, fetch, connID, useCache, cacheExpireTime, cacheHashKey, printQuery, many):
    assert isinstance(argList, tuple)
    if many:
        txn.executemany(queryString, argList)
    else:
        txn.execute(queryString, argList)
    #^ may raise an exception if the error can't be handled. don't handle that here (propagate it up)
    if fetch == 'o':
        results = txn.fetchone()
    elif fetch == 'om':
        row = txn.fetchone()
        results = fetchResultRowToDict(txn, row)
    elif fetch == 'a':
        results = txn.fetchall()
    elif fetch == 'am':
        rows = txn.fetchall()
        results = fetchResultRowsToDict(txn, rows)
    elif fetch == 'lid':
        txn.execute("SELECT LAST_INSERT_ID()")
        results = txn.fetchone()[0]
    elif fetch == 'N':
        #N = don't fetch anything
        results = None

    if useCache:
        #cache this result in memory
        assert cacheHashKey
        
        try:
            jsonResults = simplejson.dumps(results)
        except:
            #do not store in the memcache
            log.msg(u"Could not store database results in memcached; could not serialize into JSON for query: \"%s\". Args: \"%s\""
                    % (queryString, argList), lvl='w', ss='ss_db')
            return results

        #if we are running this code in the castdaemon, override the cache period with the DB-based setting
        if     cacheExpireTime == consts.MEMCACHED_DEFAULT_EXPIRE_PERIOD \
           and singleton.get('core', strict=False):
            cacheExpireTime = singleton.get('core').getPlatformSetting('castdaemon_dbcache_interval', strict=False) \
                or consts.MEMCACHED_DEFAULT_EXPIRE_PERIOD
        
        threads.blockingCallFromThread(reactor, memcache.store, cacheHashKey, jsonResults, lifetime=cacheExpireTime)
    return results


def _directProcessExecute_onError(failure, queryString, argList, fetch, connID, useCache,
cacheExpireTime, cacheHashKey, printQuery, _alreadyInBacklog):
    if failure.check(MySQLdb.ProgrammingError) or failure.check(TypeError):
        log.msg(u"Database query failure. Error: %s. Failed query was: %s; Args: (%s)"
            % (failure.getErrorMessage(), queryString, ', '.join([x for x in argList]),), lvl='e', ss='ss_db')
        failure.raiseException() #invalid syntax error
    elif failure.check(MySQLdb.OperationalError):
        if singleton.get('castdaemon', strict=False) and (singleton.get('castdaemon').isShuttingDown() or errorutil.checkIfFatalErrorOccurred()):
            #we shouldn't try to queue queries when the server is going down (as this may hold up the shutdown
            # process)
            failure.raiseException()
        
        if     _isMySQLServerConnDownErrorMessage(failure.getErrorMessage()) and not _alreadyInBacklog:
            #currently not connected, queue up the request to be run when the connection is restored
            dRequestCompleted = defer.Deferred() #will be fired when the query is finally issued against the DB
            backlogItem = {'callType': 'execute', 'queryString': queryString, 'argList': argList,
                'fetch': fetch, 'connID': connID, 'useCache': useCache,
                'cacheExpireTime': cacheExpireTime, 'cacheHashKey': cacheHashKey, 'printQuery': printQuery,
                'dRequestCompleted': dRequestCompleted, }

            log.msg(u"Connectivity failure: Queuing query (MD5: %s): \"%s\". New backlog length: %i"
                % (_getBacklogEntryLoggingHash(backlogItem),
                   sharedstrutil.truncate(sharedstrutil.removeMultipleSpacesFromString(queryString).strip(), 80),
                   singleton.get(connID).getQueryBacklogSize() + 1), lvl='i', ss='ss_db')

            singleton.get(connID)._addToQueryBacklog(backlogItem)
            return backlogItem['dRequestCompleted']
        elif _isMySQLServerConnDownErrorMessage(failure.getErrorMessage()) and _alreadyInBacklog:
            #don't insert the entry in to the backlog again as it's already there
            #print "dbExecute: CONNECTION STILL DOWN!"
            return EXECUTE_ALREADY_QUEUED_RETURNDATA
        else:
            log.msg(u"Unknown database operational error. Error: %s. Failed query was: %s; Args: (%s)"
                % (failure.getErrorMessage(), queryString,
                    ', '.join([x for x in argList]),), lvl='e', ss='ss_db')
            failure.raiseException()


def runInteraction(interaction, *args, **kwargs):
    """
    I am a wrapper to the L{twisted.enterprise.adbapi.ConnectionPool.runInteraction} function. See the
    documentation for that function for more info.
    
    @param interaction: Please remember that the function passed as this argument may not return a
    Deferred
    @return: A deferred that fires once the interaction is complete.
    
    @note: PLEASE be careful when using this function, as the function called from it must be
    thread-safe (i.e. it may not access non-local and/or non-protected resources).
    
    @note: We CANNOT backlog queries issued in an interaction spawned via this function. That means that
    if you are in the middle of an interaction and DB connectivity fails, the interaction will be aborted and
    an Exception will be generated.
    """
    connID = None
    if kwargs and kwargs.has_key('connID'):
        connID = kwargs['connID']
        del kwargs['connID']
    else:
        connID = 'dbMetastore'

    assert singleton.get(connID + 'Type') in ('direct', 'dbproxy')
    
    if singleton.get(connID + 'Type') == 'direct':
        try:    
            return singleton.get(connID).runInteraction(interaction, *args, **kwargs)
        except MySQLdb.ProgrammingError:
            raise #invalid syntax
        except MySQLdb.Error:
            #connectivity went away or other error
            raise
        except: #other error
            raise
    else: #dbproxy
        kwargs['connID'] = connID
        return singleton.get(connID).runInteraction(interaction, *args, **kwargs)


def runWithConnection(interaction, *args, **kwargs):
    """
    I am a wrapper to the L{twisted.enterprise.adbapi.ConnectionPool.runWithConnection} function. See the
    documentation for that function for more info.
    
    @param interaction: Please remember that the function passed as this argument may not return a
    Deferred
    @return: A deferred that fires once the interaction is complete.
    
    @note: PLEASE be careful when using this function, as the function called from it must be
    thread-safe (i.e. it may not access non-local and/or non-protected resources).
    
    @note: We CANNOT backlog queries issued in an interaction spawned via this function. That means that
    if you are in the middle of an interaction and DB connectivity fails, the interaction will be aborted and
    an Exception will be generated.
    """
    
    if kwargs and kwargs.has_key('connID'):
        connID = kwargs['connID']
        del kwargs['connID']
    else:
        connID = 'dbMetastore'
        
    assert connID in ('dbMetastore', 'dbLogMetastore')
    assert singleton.get(connID + 'Type') in ('direct', 'dbproxy')
    
    if singleton.get(connID + 'Type') == 'direct':
        try:    
            return singleton.get(connID).runWithConnection(interaction, *args, **kwargs)
        except MySQLdb.ProgrammingError:
            raise #invalid syntax
        except MySQLdb.Error:
            #connectivity went away or other error
            raise
        except: #other error
            raise
    else:
        return singleton.get(connID).runWithConnection(interaction, connID, *args, **kwargs)


def executeOnCursor(txn, queryString, argList=tuple(), fetch='N', useCache=False,
cacheExpireTime=consts.MEMCACHED_DEFAULT_EXPIRE_PERIOD):
    """
    Allows caching of results obtained through a direct, runInteraction-obtained cursor-level execution
        (e.g. not thorugh dbutil.execute or dbutil.callProc).
        
        @see: The arguments for L{callProc}
        @param txn: The transaction/cursor object to operate on.
        @param query: The SQL query string to execute
        @param argList: The list of arguments to operate on.
        @param fetch: The fetch mode, one of the following:
            - 'o': Return a single row of results (e.g. fetchone())
            - 'a': Return all results (e.g. fetchall())
        @return: The fetched results, according to the fetch mode
        
    @note: We CURRENTLY DO NOT/CANNOT backlog queries issued in an interaction spawned via this function. That means that
    if you are in the middle of an interaction and DB connectivity fails, the interaction will be aborted and
    an Exception will be generated.
    """
    #decode any bytestrings passed in as querystring or within arglist into unicode strings
    if isinstance(queryString, str):
        #decode into a unicode string
        queryString = queryString.decode('utf-8')
    #decode string args as well
    for i in xrange(len(argList)):
        if isinstance(argList[i], str):
            argList[i] = argList[i].decode('utf-8')
    
    if     singleton.get('core', strict=False) \
       and singleton.get('core').getPlatformSetting('castdaemon_dbcache_interval', strict=False) == 0:
        #we are running as the castdaemon and caching is disabled
        useCache = False #override any True value
    
    if useCache:
        #use the query string itself, along with the args list as the hash key
        cacheHashKey = _produceCacheHashKey(queryString, argList, fetch)
        
        #get the result from memcached in a blocking manner
        results = threads.blockingCallFromThread(reactor, memcache.retrieve, cacheHashKey)
        if results:
            results = simplejson.loads(results)
            return results
    else:
        cacheHashKey = ""
    
    #result not cached yet, execute the query and cache the results
    txn.execute(queryString, argList)
    if fetch == 'o':
        results = txn.fetchone()
    elif fetch == 'om':
        row = txn.fetchone()
        if row is None:
            return None
        cols = [ d[0] for d in txn.description ]
        results = dict(zip(cols, row))          
    elif fetch == 'a':
        results = txn.fetchall()
    elif fetch == 'am':
        rows = txn.fetchall()
        if rows is None:
            return None
        cols = [ d[0] for d in txn.description ]
        results = [dict(zip(cols, row)) for row in rows ]
    elif fetch == 'N':
        results = None        

    if useCache:
        #cache this result in memory
        assert cacheHashKey
        
        try:
            jsonResults = simplejson.dumps(results)
        except:
            #do not store in the memcache
            log.msg(u"Could not store database results in memcached; could not serialize into JSON for query: \"%s\". Args: \"%s\""
                    % (queryString, argList), lvl='w', ss='ss_db')
            return results
        
        #if we are running this code in the castdaemon, override the cache period with the DB-based setting
        if     cacheExpireTime == consts.MEMCACHED_DEFAULT_EXPIRE_PERIOD \
           and singleton.get('core', strict=False):
            cacheExpireTime = singleton.get('core').getPlatformSetting('castdaemon_dbcache_interval', strict=False) \
                or consts.MEMCACHED_DEFAULT_EXPIRE_PERIOD

        threads.blockingCallFromThread(reactor, memcache.store, cacheHashKey, jsonResults, lifetime=cacheExpireTime)
    
    return results

