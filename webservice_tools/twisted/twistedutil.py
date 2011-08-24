# -*- coding: utf-8 -*-
"""
Other common, shared utility functions

$Id:twistedutil.py 1111 2010-03-10 22:31:31Z robbyd $
@copyright:  2004-2007 Robby Dermody. 2008-Present Castdot, Inc. All Rights Reserved.
@license:    See LICENSE file for more information
"""

#############################
#MODULE DEPENDENCIES
#############################
#General deps
import os
import sys
import time
import tempfile
from twisted.python import log
from twisted.internet import defer, reactor, protocol, threads, utils as twisted_utils
from twisted.web import client as http_client
from email import MIMEText #IGNORE:E0611
import types

#Project specific deps
#from castdot.shared import consts_shared, sharedutil, sharedstrutil, singleton
from webservice_tools import utils
from webservice_tools.twisted import config, consts, errorutil, twistedstrutil, singleton


#############################
#MODULE-LEVEL VARIABLES
#############################


#############################
#MODULE FUNCTIONALITY
#############################
def deferredWait(result, numSeconds, textToPrintOnWait=None, lvl='i', ss='ss_default'):
    """
    This function is a dummy which simulates a delayed result
    
    Usage: d.addCallback(twistedutil.deferredWait, 5, "Waiting for event...")
    
    @param result: The result to ultimately return once the deferred operation completes.
    @param numSeconds: Number of seconds to delay
    @param textToPrintOnWait: Optional text to log once we start the delay period
    @return: a Deferred which will fire with result once numSeconds seconds elapse
    """
    if textToPrintOnWait:
        log.msg(textToPrintOnWait, lvl=lvl, ss=ss)
        
    d = defer.Deferred()
    # simulate a delayed result by asking the reactor to fire the
    # Deferred in n seconds time
    reactor.callLater(numSeconds, d.callback, result) #IGNORE:E1101
    return d


def deferredWaitForFile(result, fileName, maxNumSeconds, textToPrintOnWait=None, pollPeriod=.5,
                        fatalErrorOnFailure=True, waitForFileExists=True):
    """
    This function waits up to a certain period for a file to exist. Alternatively, it can wait for a
    certain amount of time for a file NOT to exist.
    
    Usage: d.addCallback(twistedutil.deferredWaitForFile, "/tmp/bla.out", 5, "Waiting for file...")
    
    @param result: The result to ultimately return once the deferred operation completes.
    @param fileName: The file name to wait to be available
    @param maxNumSeconds: Maximum number of seconds to delay before giving up (and raising an exception)
    @param pollPeriod: How often to poll, in seconds
    @param textToPrintOnWait: Optional text to log once we start the delay period
    @param waitForFileExists: If True, wait for the file to exist. If False, wait for the file NOT to exist.
    @return: a Deferred which will fire with result once numSeconds seconds elapse
    """
    assert pollPeriod <= maxNumSeconds
    
    def _checkForFile(result, numSecondsRemaining):
        if  ((waitForFileExists == True  and     os.path.exists(fileName))
        or   (waitForFileExists == False and not os.path.exists(fileName))):
            #the file exists, ok we can quit
            return defer.succeed(True)
        else:
            numSecondsRemaining = numSecondsRemaining - pollPeriod
            if numSecondsRemaining <= 0:
                if fatalErrorOnFailure:
                    errorutil.triggerFatalError("File \"%s\" took too long to appear/disappear. Giving up..." % fileName)
                else:
                    raise Exception("File \"%s\" took too long to appear/disappear. Giving up..." % fileName)
            d = defer.Deferred()
            d.addCallback(_checkForFile, numSecondsRemaining)
            reactor.callLater(pollPeriod, d.callback, result) #IGNORE:E1101
            return d
    
    if textToPrintOnWait:
        log.msg(textToPrintOnWait, lvl='i', ss='ss_default')
        
    d = _checkForFile(None, maxNumSeconds)
    return d


def deferredWaitForTCPConn(result, hostName, port, maxNumSeconds, textToPrintOnWait=None, pollPeriod=.75,
                           fatalErrorOnFailure=True, waitForCanMakeConn=True):
    """
    This function waits up to a certain period to be able to connect to a specific port on a specific
    host via TCP. Alternatively, it can wait a certain amount of time until it is NOT able to connect to a host.
    
    Usage: d.addCallback(twistedutil.deferredWaitForTCPConn, "localhost", 1234, 5, "Waiting for Foobar daemon to start...")
    @param hostName: The hostName to attempt to connect to
    @param port: The port on the given host to attempt to connect to
    @param result: The result to ultimately return once the deferred operation completes.
    @param maxNumSeconds: Maximum number of seconds to delay before giving up (and raising an exception)
    @param pollPeriod: How often to poll, in seconds
    @param textToPrintOnWait: Optional text to log once we start the delay period
    @param waitForCanMakeConn: If set to True, wait until we are able to connect to a host before succeeding
    (this is the normal case). If set to False, wait until we are NOT able to connect to a host before succeeding.
    @return: a Deferred which will fire with result once numSeconds seconds elapse
    """
    import socket
    assert pollPeriod <= maxNumSeconds
    
    def _checkForTCPConn():
        import errno
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #s.setblocking(0)
        s.settimeout(pollPeriod)
        numSecondsElapsed = 0
        t0 = 0
        t1 = 0
        
        while numSecondsElapsed < maxNumSeconds:
            if waitForCanMakeConn:
                try:
                    t0 = time.time()
                    s.connect((hostName, port))
                    
                    #we made the connection, so we're all good...
                    s.close()
                    return
                except socket.error:
                    #couldn't make the connection, try again...
                    t1 = time.time()
                    if t1 - t0 <= pollPeriod:
                        time.sleep(pollPeriod - (t1 - t0))
                    numSecondsElapsed += pollPeriod
            else:
                try:
                    t0 = time.time()
                    s.connect((hostName, port))
                    
                    #we made the connection still...
                    s.close()

                    #wait to try again...
                    t1 = time.time()
                    if t1 - t0 <= pollPeriod:
                        time.sleep(pollPeriod - (t1 - t0))
                    numSecondsElapsed += pollPeriod
                except socket.error:
                    #assume that we couldn't make the connection, so this is good in this case
                    return

        if waitForCanMakeConn:
            #if we're here, we were waiting to connect and the connect kept failing, so we gave up
            if fatalErrorOnFailure:
                errorutil.triggerFatalError("Couldn't connect to host \"%s\", port %s in alotted time. Giving up..." % (hostName, port))
            else:
                raise Exception("Couldn't connect to host \"%s\", port %s in alotted time. Giving up..." % (hostName, port))
        else:
            #if we're here, we were waiting to NOT be able to connect and the connect kept succeeding, so we gave up
            if fatalErrorOnFailure:
                errorutil.triggerFatalError("Couldn't NOT connect to host \"%s\", port %s in alotted time. Giving up..." % (hostName, port))
            else:
                raise Exception("Couldn't NOT connect to host \"%s\", port %s in alotted time. Giving up..." % (hostName, port))
                
    if textToPrintOnWait:
        log.msg(textToPrintOnWait, lvl='i', ss='ss_default')
        
    d = threads.deferToThread(_checkForTCPConn)
    return d


def touchAndSetPerms(filePath, user='root', group='root', mode='600', onlyIfNotExistent=True):
    """Like the touch command in UNIX. This is a more advanced version that allows us to set the permissions
    and file mode"""
    if onlyIfNotExistent and os.path.exists(filePath):
        #file already exists
        return
    
    cmdString = "sudo touch %s; sudo chown %s:%s %s; sudo chmod %s %s;" % (filePath,
        user, group, filePath, mode, filePath)
    d = runCmdInTwisted(cmdString)
    d.addCallback(_cbTouchAndSetPerms, filePath, cmdString)
    return d


def _cbTouchAndSetPerms((out, err, statusCode), filePath, cmdString):
    if statusCode:
        errorutil.triggerFatalError("Could touch file \"%s\"."
            " Stdout: \"%s\"; Stderr: \"%s\"" % (filePath, out, err))
    return True
    

def replaceContentsOfPrivilegedFile(fileName, newContents, fatalErrorOnFailure=True,
                                    atomicFromDir=None, user='root', group='root', mode='600'):
    """Replaces the contents of a file which requires root (or similar) access to manipulate with new data.
    @param newContents: A string containing the new contents of the file. The existing file will be
     overwritten with these contents (e.g. NOT appended)
    @param fileName: This file does not need to already exist on the filesystem.
    
    @param user: The username/UID that should own the file. If a file at fileName doesn't exist, then
    this value will be used to set the owner of the newly created file.
    @param group: The group name/GID that should own the file. If a file at fileName doesn't exist, then
    this value will be used to set the owning group of the newly created file.
    @param mode: The desired permissions mode of the file (expressed as a 3 digit octal string).
    If a file at fileName doesn't exist, then this value will be used to set the mode of the newly created file.
    @param atomicFromDir:  If set, the tmpfile is created in atomicFromDir and an atomic rename(2) is attempted via mv(1).
    """
    
    #the dir the file is in must exist
    assert os.path.exists(os.path.dirname(fileName))
    assert user and isinstance(user, (str))
    assert group and isinstance(group, (str))
    assert mode and isinstance(mode, (str)) and len(mode) in (3, 4)

    (tmpFileFD, tmpFilePath) = tempfile.mkstemp (dir=atomicFromDir)
    tmpFile = os.fdopen(tmpFileFD, 'w')
    tmpFile.write(newContents)
    tmpFile.close()
    
    #TODO: this currently won't properly overwrite any symlinks...let's keep this by design for now
    if isinstance (atomicFromDir, basestring):
        cmdString = "sudo chown %s:%s %s;" % (user, group, tmpFilePath)
        cmdString += "sudo chmod %s %s;" % (mode, tmpFilePath)
        cmdString += "sudo mv %s %s;" % (tmpFilePath, fileName)
        print "JKH replaceContentsOfPrivilegedFile: cmdString = ", cmdString
    else:
        cmdString = """\
        if [ -e %s ]; then \
            sudo cp --no-preserve=mode,ownership %s %s; \
            sudo rm -f %s; \
        else \
            sudo chown %s:%s %s; \
            sudo chmod %s %s; \
            sudo cp --preserve=mode,ownership,timestamps %s %s; \
            sudo rm -f %s; \
        fi \
        """ % (fileName, tmpFilePath, fileName, tmpFilePath,
               user, group, tmpFilePath, mode, tmpFilePath, tmpFilePath, fileName, tmpFilePath)
        
    d = runCmdInTwisted(cmdString)
    d.addCallback(_cbReplaceContentsOfPrivilegedFile, fileName, cmdString)
    return d


def _cbReplaceContentsOfPrivilegedFile((out, err, statusCode), fileName, cmdString):
    if statusCode:
        errorutil.triggerFatalError("Could not replace contents of privileged file \"%s\"."
            " Stdout: \"%s\"; Stderr: \"%s\"" % (fileName, out, err))



def makeHTTPRequestToURL(requestURL, timeout=5, method='GET', postData=None, headers=None, cookies=None,
followRedirect=True, maxRetries=0, timeoutBetweenRetries=0):
    """I make a HTTP GET request to the given URL.
   
    @param requestURL: The URL to send the request to
    @param timeout: The connect timeout (by default, 5 seconds). Set to 0 for no timeout. This is NOT
     the timeout between retries
    @param method: 'GET' or 'POST', defaults to 'GET'. If 'POST' is specified, postData must be set
    @param postData: The data that is sent in a POST request. Only valid if method is set to 'POST'. If specified,
    this can either be a string or unicode object (in which case it is sent as-is after being encoded to utf-8),
    or a dict, in which case it is URLEncoded into a utf-8 string and sent.
    @param headers: Any extra/overridden data for the request's HTTP headers. This must be a dictionary, or None.
        All entries in this dictionary should be strings, NOT unicode.
    @param cookies: Any cookies to be used with the request. This must be a dictionary, or None.
    @followRedirect: True by default to follow any redirects. Set to False to not follow.
    @maxRetries: The max # of retries (which we get failures with) before giving up
    @timeoutBetweenRetries: How long (in seconds) we wait before retries. This is in addition to our connect
    timeout, to the extent that it applies. 
    
    @return: A deferred which will yield the data sent back from this host, or None on failure.
    @type return: String
    """
    d = makeHTTPRequestToURLExtended(requestURL, timeout, method, postData, headers, cookies,
                                     followRedirect, maxRetries, timeoutBetweenRetries)
    d.addCallback(lambda response:  response['data'])
    d.addErrback(lambda response: None)
    return d


def makeHTTPRequestToURLExtended(requestURL, timeout=5, method='GET', postData=None, headers=None, cookies=None,
followRedirect=True, maxRetries=0, timeoutBetweenRetries=0):
    """I make a HTTP GET request to the given URL.
    
    @param requestURL: The URL to send the request to
    @param timeout: The connect timeout (by default, 5 seconds). Set to 0 for no timeout. This is NOT
     the timeout between retries
    @param method: 'GET' or 'POST', defaults to 'GET'. If 'POST' is specified, postData must be set
    @param postData: The data that is sent in a POST request. Only valid if method is set to 'POST'. If specified,
    this can either be a string or unicode object (in which case it is sent as-is after being encoded to utf-8),
    or a dict, in which case it is URLEncoded into a utf-8 string and sent.
    @param headers: Any extra/overridden data for the request's HTTP headers. This must be a dictionary, or None.
        All entries in this dictionary should be strings, NOT unicode.
    @param cookies: Any cookies to be used with the request. This must be a dictionary, or None.
    @followRedirect: True by default to follow any redirects. Set to False to not follow.
    @maxRetries: The max # of retries (which we get failures with) before giving up
    @timeoutBetweenRetries: How long (in seconds) we wait before retries. This is in addition to our connect
    timeout, to the extent that it applies. 
    
    @return: A deferred which will yield a dict in the form of {'success': <bool>, 'data': <responseBody>|<failureObject>}
    @type return: String
    """
    def getPage(url, contextFactory=None, *args, **kwargs):
        """Download a web page as a string.
    
        Download a page. Return a deferred, which will callback with a
        page (as a string) or errback with a description of the error.
    
        See HTTPClientFactory to see what extra args can be passed.
        
        @note: This function taken from Twisted source code (twisted/web/client.py) and modified
        so that it wouldn't be noisy. Twisted source code is BSD licensed.
        """
        
        scheme, host, port, path = http_client._parse(url)
        factory = http_client.HTTPClientFactory(url, *args, **kwargs)
        #CASTDOT-CUSTOM: make it so this function is not noisy
        factory.noisy = False
        if scheme == 'https':
            from twisted.internet import ssl
            if contextFactory is None:
                contextFactory = ssl.ClientContextFactory()
            reactor.connectSSL(host, port, factory, contextFactory) #IGNORE:E1101
        else:
            reactor.connectTCP(host, port, factory) #IGNORE:E1101
        return factory.deferred

    def finished(responseText):
        log.msg("HTTP Request to \"%s\" (timeout=%s) finished: response: \"%s\"" % (requestURL,
            timeout, utils.truncate(responseText, 180)), lvl='d', ss='ss_webreq')
        return {'success': True, 'data': responseText}
    
    def failed(reason, counter=1):
        log.msg(reason.value['response'])
        if counter <= maxRetries:
            #try again...
            log.msg("Retrying HTTP request to \"%s\" (timeout=%s, retryTimeout=%s) (retry %i of %i). Failure reason: %s" % (
                requestURL, timeout, timeoutBetweenRetries, counter, maxRetries, reason), lvl='d2', ss='ss_webreq')
            if timeoutBetweenRetries:
                d = deferredWait(None, timeoutBetweenRetries)
            else:
                d = defer.succeed(True)
            d.addCallback(lambda result: getPage(requestURL, timeout=timeout, method=method, postdata=postData,
                headers=headers, cookies=cookies, followRedirect=int(followRedirect)))
            d.addCallback(finished)
            d.addErrback(failed, counter=(counter + 1))
            return d
        #no retries or retries exhausted
        log.msg("HTTP Request HTTP request to \"%s\" (timeout=%s) failed after %i retries: reason: %s" % (requestURL,
            timeout, maxRetries, reason,), lvl='d', ss='ss_webreq')
        return {'success': False, 'data': reason} #failure
    assert requestURL and isinstance(requestURL, (unicode, str))
    assert isinstance(timeout, (int, long)) and timeout >= 0
    assert method in ('GET', 'POST')
    assert postData is None or (isinstance(postData, (basestring, dict)) and method == 'POST')
    assert headers is None or isinstance(headers, dict)
    assert cookies is None or isinstance(cookies, dict)
    assert isinstance(followRedirect, bool)
    assert isinstance(maxRetries, (int, long)) and maxRetries >= 0
    assert isinstance(timeoutBetweenRetries, (int, long)) and timeoutBetweenRetries >= 0
    if isinstance(requestURL, unicode):
        try:
            requestURL = str(requestURL)
        except:
            raise Exception("Invalid requestURL: Cannot be converted to a str")
    
    #Content type should be "application/x-www-form-urlencoded" in the cases of POST data
    # (but don't override what may be there)
    if method == 'POST' and (not headers or 'Content-Type' not in headers):
        if not headers:
            headers = {}
        headers['Content-Type'] = "application/x-www-form-urlencoded"
    
    #open up a connection to the source store to get the recording data
    log.msg("Making HTTP request to \"%s\" (timeout=%s) (maxRetries=%i, retryTimeout=%i)..." % (requestURL,
        timeout, maxRetries, timeoutBetweenRetries),
        lvl='d2', ss='ss_webreq')
    
    if isinstance(postData, basestring):
        postData = postData.encode('utf-8')
    elif isinstance(postData, dict):
        postData = utils.friendlyURLEncode(postData)
    
    d = getPage(requestURL, timeout=timeout, method=method, postdata=postData, headers=headers, cookies=cookies,
        followRedirect=int(followRedirect))
    d.addCallback(finished)
    d.addErrback(failed)
    return d    
    

def makeHTTPRequest(destHostname, destPort, requestURI, timeout=5, method='GET', postData=None, headers=None,
cookies=None, followRedirect=True, maxRetries=0, timeoutBetweenRetries=0, secure=False):
    """I make a HTTP request to the given host. (http://host:port/URI)
    
    @param destHostname: The host to send the request to
    @param destPort: The port on the specified host
    @param requestURI: The request URI
    @param timeout: The connect timeout (by default, 5 seconds). Set to 0 for no timeout.
    @param method: 'GET' or 'POST', defaults to 'GET'. If 'POST' is specified, postData must be set
    @param postData: The data that is sent in a POST request. Only valid if method is set to 'POST'. If specified,
    this must be set to a string that has been passed through urllib.urlencode().
    @param headers: Any extra/overridden data for the request's HTTP headers. This must be a dictionary, or None.
        All entries in this dictionary should be strings, NOT unicode.
    @param cookies: Any cookies to be used with the request. This must be a dictionary, or None.
    @followRedirect: True by default to follow any redirects. Set to False to not follow. 
    
    @return: A deferred which will yield the data sent back from this host, or None on failure.
    @type return: String
    """
    
    scheme = secure and  'https' or 'http'
    
    url = "%s://%s:%s%s%s" % (scheme, destHostname, destPort, not requestURI.startswith('/') and '/' or '', requestURI)
    d = makeHTTPRequestToURL(url, timeout=timeout, method=method, postData=postData, headers=headers,
        cookies=cookies, followRedirect=followRedirect, maxRetries=maxRetries,
        timeoutBetweenRetries=timeoutBetweenRetries)
    return d


def downloadToFile(url, file, contextFactory=None, *args, **kwargs):
    """Download a web page to a file.

    @param file: path to file on filesystem, or file-like object.

    See HTTPDownloader to see what extra args can be passed.
    
    @note: This function taken from downloadToPage function in Twisted source code (twisted/web/client.py) and modified
    so that it wouldn't be noisy. Twisted source code is BSD licensed.
    """
    log.msg("Making HTTP request to \"%s\" -- downloading returned data to \"%s\"..." % (url, file),
        lvl='d2', ss='ss_webreq')

    scheme, host, port, path = http_client._parse(url)
    factory = http_client.HTTPDownloader(url, file, *args, **kwargs)
    #CASTDOT-CUSTOM: make it so this function is not noisy
    factory.noisy = False
    if scheme == 'https':
        from twisted.internet import ssl
        if contextFactory is None:
            contextFactory = ssl.ClientContextFactory()
        reactor.connectSSL(host, port, factory, contextFactory) #IGNORE:E1101
    else:
        reactor.connectTCP(host, port, factory) #IGNORE:E1101
    return factory.deferred


def runCmdInTwisted(cmdString, fullEnviron=True, printCommand=False, fatalErrorOnFailure=False, maskOutText=""):
    """A simple wrapper to twisted.internet.utils.getProcessOutputAndValue that runs the given command through
    the bash shell interpreter. See the twisted function's documentation for more info.
    
    @param cmdString: The command to run
    @param fullEnviron: Run the command with the full environment variable setup that the castdaemon was spawned with
    @param printCommand: Always print the command (regardless of the ss_cmds logging level)
    @param fatalErrorOnFailure: Set to True to trigger a fatal error if the command fails to execute
    @return: A deferred, which yields a tuple containing the program's output (from stdout and stderr) and
        it's exit code as (out, err, code). On execution error, ("ERROR", "ERROR", 65535) is returned. 
        
    @note: BUG: It used to be that using getProcessOutputAndValue seems to cause glib race conditions sometimes:
    Inconsistency detected by ld.so: dl-open.c: 215: dl_open_worker: Assertion `_dl_debug_initialize
    (0, args->nsid)->r_state == RT_CONSISTENT' failed!
    
    Is this still the case?
    """
    def commandFailure(failure, cmdString):
        if fatalErrorOnFailure:
            errorutil.triggerFatalError("Execution of command \"%s\" failed to execute: \"%s\"" % (cmdString, failure))
        else:
            log.msg("Execution of command \"%s\" failed to execute: \"%s\"" % (cmdString, failure),
                lvl='e', ss='ss_default')
            return ("ERROR", "ERROR", 65535)
        
    log.msg("About to run command \"%s\" (fullEnviron: %s)"
        % (cmdString, fullEnviron and "yes" or "no"), lvl='d2', ss='ss_cmds')
    
    #twisted wants the command string as a string, not unicode
    cmdString = str(cmdString)
    
    d = twisted_utils.getProcessOutputAndValue("bash", ['-c', cmdString], env=fullEnviron and os.environ or {})
    d.addCallback(_cbRunCmdInTwisted, cmdString, fullEnviron, printCommand, maskOutText)
    d.addErrback(commandFailure, cmdString)
    return d


def _cbRunCmdInTwisted(cmdResult, cmdString, fullEnviron, printCommand, maskOutText):
    if maskOutText:
        maskedCmdString = cmdString.replace(maskOutText, '****')
    else:
        maskedCmdString = cmdString
    
    log.msg("Finished running command \"%s\". fullEnviron: %s, RC: %s, Stdout: \"%s\", StdErr: \"%s\""
        % (maskedCmdString, fullEnviron and "yes" or "no", cmdResult[2], cmdResult[0], cmdResult[1]),
        lvl=printCommand and 'a' or 'd', ss='ss_cmds')
    return cmdResult

def simpleReadConfigFile(filename):
    """Reads in config file 
    
    @return: A dict containing the entries of the file read in. If the file could not be found or otherwise
    parsed, an empty dict is returned.
    """
    import ConfigParser
    loadedConfig = {}
    cp = ConfigParser.SafeConfigParser()
    filesParsed = cp.read(filename)
    if len(filesParsed) == 0:
        #could not parse out the file
        return {}
    
    for sec in cp.sections():
        name = str.lower(sec)
        for opt in cp.options(sec):
            loadedConfig[name + "." + opt.lower()] = cp.get(sec, opt).strip()
    
    return loadedConfig