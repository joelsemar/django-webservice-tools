# -*- coding: utf-8 -*-
"""
Module which allows easy reading and writing of configuration files
and stores the loaded configuration after config file reading

This module makes used of Python's ConfigParser module, which stores configuration data in an .ini like
file format

$Id:config.py 977 2010-02-09 20:43:13Z robbyd $
@copyright:  2004-2007 Robby Dermody. 2008-Present Castdot, Inc. All Rights Reserved.
@license:    See LICENSE file for more information
"""

#############################
#MODULE DEPENDENCIES
#############################
#General deps
import sys
import os
import ConfigParser
from twisted.python import log

#Project specific deps
from webservice_tools.twisted import consts
from webservice_tools.twisted.twistedutil import simpleReadConfigFile


#############################
#MODULE-LEVEL VARIABLES
#############################
_loaded = {}


#############################
#MODULE FUNCTIONALITY
#############################
def load(filename, defaultConfig={}, writeIfNonExistent=True, quitIfNonExistent=False):
    """I read in a stored configuration from a file
    
    @param filename: The name of the configuration file to read
    
    @param defaultConfig: A dict supplying ALL of the possible value configuration items which could be in
    this file (as the item's key), along with a default value for each (as the item's value).
    Please note that all keys and values in defaultConfig must be in string format.
    
    @param writeIfNonExistent: Set to True to write the configuration file if it doesn't exist. Set to
    False to generate an exception if the file doesn't exist
    
    @param quitIfNonExistent: Set to True to quit the program if the configuration file doesn't exist.
    If this is True, and writeIfNonExistent is False, then the app will just quit with no configuration 
    file being written.
    """
    global _loaded
    assert filename and isinstance(filename, basestring)

    #all keys and values in defaultConfig must be strings
    #(to make it match what would be read in by ConfigParser)
    #lets error out if we find a key or value that isn't a string
    for (key, value) in defaultConfig.iteritems():
        if not isinstance(key, basestring):
            raise KeyError("Invalid defaultConfig: key \"%s\" is not a string" % str(key))
        if not isinstance(value, basestring):
            raise ValueError("Invalid defaultConfig: value of key \"%s\" (\"%s\") is not a string" 
                % (str(key), str(value)))

    _loaded = defaultConfig.copy()
    
    configFileExists = os.path.exists(filename)
    
    #If we just want to "load" the default configuration
    if writeIfNonExistent and not configFileExists:
        log.msg("Configuration file \"%s\" does not exist..." % filename, lvl='w', ss='ss_configfile')
        try:
            write(filename)
        except:
            raise
        
        #if quitIfNonExistent is set, keep going to the next block of code
        #so we can quit out properly
        if not quitIfNonExistent:
            return

    if quitIfNonExistent and not configFileExists:
        #print different messages depending on if the default
        #config file was written or not
        if writeIfNonExistent:
            log.msg("Quitting as configuration file did not exist. Please "
                         "edit the default configuration that has been written "
                         "to \"%s\" to suit your environment and start the program "
                         "again." % filename, lvl='c', ss='ss_configfile')
            sys.exit(0)
        else:
            log.msg("Quitting as configuration file \"%s\" does not exist."
                " Please create this file and try again." % filename)
            sys.exit(1)

    log.msg("Reading configuration from \"%s\"..." % filename, lvl='i', ss='ss_configfile')
    _loaded = simpleReadConfigFile(filename, useLogging=True,
                                              level=consts.LOGLVL_DEBUG3)
            
    log.msg("ACTIVE CONFIGURATION: " + str(_loaded),
               lvl='d2', ss='ss_configfile')


def write(filename):
    """I write the configuration stored in this module's "_loaded" variable to a file.
    
    @param filename: The name of the file to write the configuration data to. Any data already in this
    file will be overwritten.
    """
    log.msg("Saving configuration information to \"" + filename + "\"", lvl='i', ss='ss_configfile')

    f = open(filename, 'w')
    cp = ConfigParser.SafeConfigParser()
    #a little string hacking because our section names are un-normalized
    #this builds a list of all the sections names
    sectionslst = []
    sections = []
    for k in _loaded.keys():
        sectionslst.append(k.split('.')[0])
    #get unique entries
    sections = _uniquer(sectionslst)
    for sec in sections:
        log.msg("\tCompiling section \"" + sec + "\"",
                   lvl='d3', ss='ss_configfile')
        #make the headers
        cp.add_section(sec)
        #for each item in my dictionary
        #it splits the key in two and uses that for the first and second "set" args
        #then it uses the item.value for the 3rd arg
        # from 'section.option:value'
    
    for k in _loaded.items():
        cp.set(str(k[0]).split('.')[0], str(k[0]).split('.')[1], str(k[1]))
    cp.write(f)
    f.close()


def _uniquer(seq):
    def idfun(x):
        return x
    
    seen = {}
    result = []
    for item in seq:
        marker = idfun(item)
        if marker in seen: continue
        seen[marker] = 1
        result.append(item)
    return result


def get(settingName, strict=True):
    """Gets the setting of a parameter from the loaded configuration.
    
    @param settingName: The configuration parameter to retrieve the setting of, specified in the format of
    <section>.<name> (e.g. 'main.pid_file' for the 'pid_file' parameter under the 'main' section).
    @param strict: If set to True (default), then raise an error if the specified settingName value is invalid.
    If set to False, simply return None
    @return: The value of this parameter.
    """
    if strict and settingName not in _loaded:
        raise ValueError("Specified configuration setting \"%s\" does not exist" % settingName)
    
    return _loaded.get(settingName, None)


def set(settingName, value):
    """Set a configuration parameter.
    
    @param settingName: The configuration parameter to set, specified in the format of
    <section>.<name> (e.g. 'main.pid_file' for the 'pid_file' parameter under the 'main' section).
    @param value: The new value of this configuration parameter
    """
    if settingName not in _loaded:
        raise ValueError("Specified configuration setting \"%s\" does not exist" % settingName)
    
    _loaded[settingName] = value
    
    
def isLoaded():
    """Tests if the configuration has been loaded.
    @return: True if an active configuration has been loaded (_loaded is not None)
    """
    return _loaded is not None


