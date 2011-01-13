# -*- coding: utf-8 -*-
"""
Error utility functions

$Id:errorutil.py 959 2010-02-06 19:21:09Z robbyd $
@copyright:  2004-2007 Robby Dermody. 2008-Present Castdot, Inc. All Rights Reserved.
@license:    See LICENSE file for more information
"""

#############################
#MODULE DEPENDENCIES
#############################
#General deps
import os
import sys
import traceback
import time
import xmlrpclib
from twisted.python import failure, log
#from twisted.internet import reactor
#exit is used to stop the program on fatal errors until the reactor runs
from sys import exit as stopfunc

#Project specific deps
from webservice_tools.twisted import consts, singleton


#############################
#MODULE-LEVEL VARIABLES
#############################
_fatalErrorOccurred = False
_doMinimalShutdown = False


#############################
#MODULE FUNCTIONALITY
#############################
def triggerFatalError(errorStr, printError=True, doMinimalShutdown=False):
    """I am called on an unrecoverable error. I will signal the error, wait a certain period of time
    (like 2 seconds), and then exit the program. As monit should be running for the process, and it will
    automatically restart it.
    
    @param errorStr: The error string to print out as the error that occurred
    @type errorStr: str
    
    @param doMinimalShutdown: Set to True to have the role not deinitalize the core role
    """
    from twisted.internet import reactor
    global stopfunc
    global _fatalErrorOccurred
    global _doMinimalShutdown
    assert stopfunc
    
    if _fatalErrorOccurred:
        #fatal error already occurred, we should already be in the process of shutting down, so just return here
        return
    
    _fatalErrorOccurred = True
    _doMinimalShutdown = doMinimalShutdown
    log.msg("FATAL ERROR RAISED: %s" % errorStr, lvl='c', ss='ss_castdaemon')
    
    #for the castdaemon, send it out to our zenoss monitoring server if we're configured to do that
    try:
        createZEventOnException = singleton.get('core').getPlatformSetting('create_zevent_on_castdaemon_exception')
    except:
        #probably that the settings cache is not initialized
        createZEventOnException = False
        
    if     singleton.get('castdaemon', strict=False) \
       and createZEventOnException:
        from castdaemon import util as castdaemon_util
        for zenossHostCol in ('health_monitoring_server1', 'health_monitoring_server2'):
            zenossHost = singleton.get('core').getPlatformSetting(zenossHostCol)
            castdaemon_util.sendEventToZenoss(zenossHost, singleton.get('core').getPlatformSetting('zenoss_manager_login'),
                singleton.get('core').getPlatformSetting('zenoss_manager_password'),
                "Castdaemon Exception: %s" % errorStr, str(traceback.format_exc()), 'error')
    
    if printError and getattr(sys, "exc_value", None):
        #print out the traceback of the last exception thrown
        log.msg(traceback.format_exc())
        
    log.msg("EXITING (TO BE RESTARTED AUTOMATICALLY)", lvl='i', ss='ss_castdaemon')
    #time.sleep(consts_shared_twisted.PERIOD_SLEEP_ON_FATAL_ERROR)
    
    try:
        stopfunc() #either reactor.stop() or sys.exit()
    except: #if the reactor isn't running, we will get an exception we can ignore here
        pass
    if stopfunc == reactor.stop: #IGNORE:E1101
        #now raise an exception so that 
        raise Exception("HALT - FATAL ERROR RAISED: %s" % errorStr)
    #then the app will end, and monit will restart it
    
    
def checkIfFatalErrorOccurred():
    """I am called to see if a fatal error has occurred.
    
    @return: True if a fatal error occurred, False otherwise.
    """
    return _fatalErrorOccurred


def checkIfMinimalShutdownRequired():
    return _doMinimalShutdown


def setFatalErrStopFunc(stopFunction):
    """Sets the function used to stop the program on a fatal error
    By default, sys.exit() is used without this functio having to be called. Once the twisted reactor starts
    running, this function should be called to set the stop function to reactor.stop() instead.
    
    The castdaemon does not need to call this function directly, as it is called for through
    L{castdot.shared.twisted.twistedutil.emulateTwistd}.
    """
    global stopfunc
    stopfunc = stopFunction
    