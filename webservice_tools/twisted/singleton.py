# -*- coding: utf-8 -*-
"""
Singleton implementation. See U{http://www.object-arts.com/EducationCentre/Patterns/Singleton.htm} for some
more information on what a singleton is.

>>> listEntries()
Singleton Store contents: {}

>>> store(True, [1, 2, 3])
Traceback (most recent call last):
    ...
AssertionError

>>> store(1, [1, 2, 3])
Traceback (most recent call last):
    ...
AssertionError

>>> store('foo', [1, 2, 3])
Storing key "foo" in singleton store

>>> listEntries()
Singleton Store contents: {'foo': [1, 2, 3]}

>>> get('foo')
[1, 2, 3]

>>> store('foo', [1, 2, 3], replaceIfExists=False)
Traceback (most recent call last):
    ...
KeyError: 'Key "foo" already present in singleton store!'
>>> store('foo', "TEST")
Storing key "foo" in singleton store

>>> get('foo')
'TEST'
>>> remove('NOTEXIST', errorLevelIfNonExistent='n')
Removing key "NOTEXIST" from singleton store

>>> remove('NOTEXIST')
Traceback (most recent call last):
    ...
KeyError: 'Key "NOTEXIST" does not exist in singleton store'
>>> remove('foo')
Removing key "foo" from singleton store

>>> get('foo', strict=False)

>>> get('foo')
Traceback (most recent call last):
    ...
KeyError: 'Key "foo" does not exist in singleton store'

"""

#############################
#MODULE DEPENDENCIES
#############################
#General deps
from __future__ import absolute_import  #MUST be first import
import logging

#Project specific deps

#############################
#MODULE-LEVEL VARIABLES
#############################
_singletonStore = {}


#############################
#MODULE FUNCTIONALITY
#############################
def _isRunningCastdaemon():
    return 'castdaemon' in _singletonStore and 'core' in _singletonStore and 'castdaemonFullyInit' in _singletonStore and _singletonStore['castdaemonFullyInit'] == True


def _logMsg(msg, lvl, ss):
    if _isRunningCastdaemon():
        #Work around because trying to use twisted.python.log() breaks on castdaemon startup/shutdown
        from twisted.python import log
        log.msg(msg, lvl=lvl, ss=ss)
        #logging.debug(msg)
    else:
        print msg


def _fatalError(msg):
    if _isRunningCastdaemon():
        from castdot.shared.twisted import errorutil
        errorutil.triggerFatalError(msg)
    else:
        import sys
        sys.exit(msg)


def store(key, item, replaceIfExists=True):
    """I store an item in the singleton
    @param key: The key to store the item under (e.g. "MyItem", "clientDict", etc)
    @type key: str
    
    @param item: The actual item to store, this can be an object of any type
    
    @param replaceIfExists: If there is an item with this key already in the singleton, set this parameter
    to True to replace it. If set to False, a KeyError will be raised
    """
    global _singletonStore
    assert isinstance(key, basestring)
    assert item != None
    
    _logMsg("Storing key \"%s\" in singleton store" % key, lvl='d2', ss='ss_default')

    if _singletonStore.has_key(key) and not replaceIfExists:
        raise KeyError("Key \"%s\" already present in singleton store!" % key)
        
    _singletonStore[key] = item


def remove(key, errorLevelIfNonExistent='r'):
    """I remove an item from the singleton
    
    @param key: The key of the item to remove
    @type key: str
    
    @param errorLevelIfNonExistent: One of the following:
        'f' - Generate a fatal error if no item with the specified key exists.
        'r' - Raise a KeyError if no item with the specified key exists.
        'n' - Do nothing if no item with the specified key exists. (Quiet.)
    """
    global _singletonStore
    assert isinstance(key, basestring)
    assert errorLevelIfNonExistent in ('f', 'r', 'n')

    _logMsg("Removing key \"%s\" from singleton store" % key, lvl='d2', ss='ss_default')

    if not _singletonStore.has_key(key):
        if errorLevelIfNonExistent == 'f':
            _fatalError("Key \"%s\" does not exist in singleton store" % key)
        elif errorLevelIfNonExistent == 'r':
            raise KeyError("Key \"%s\" does not exist in singleton store" % key)
        elif errorLevelIfNonExistent == 'n':
            return

    item = _singletonStore.pop(key, None)
    #now explicitly destroy the item
    if item:
        del item


def get(key, strict=True, fatalErrorOnFailure=False):
    """I return the item with the specified key. If the item cannot be found, a fatal error or an exception
    is generated
    
    @param key: The key of the item to get
    @param strict: Set to True to raise a ValueError (or generate a fatal error, depending on the setting
    of 'fatalErrorOnFailure') if the specified key cannot be found. If set to False, None will be returned
    if the key cannot be found.
    @param fatalErrorOnFailure: If set to True, generate a fatal error if the item cannot be found. Otherwise,
    a ValueError is raised. The 'strict' parameter must be set to True for this parameter to be relevant.
    
    @return: A reference to the item, or None
    """
    global _singletonStore
    assert isinstance(key, basestring)

    if strict and key not in _singletonStore:
        errorStr = "Key \"%s\" does not exist in singleton store" % key
        if not fatalErrorOnFailure:
            raise KeyError(errorStr)
        else:
            _fatalError(errorStr)
        
    return _singletonStore.get(key, None)


def listEntries():
    """I print a list of the entires in the singleton to the screen
    """
    global _singletonStore
    print "Singleton Store contents:", _singletonStore
