# -*- coding: utf-8 -*-
"""
Utility functions and classes for strings

$Id:twistedstrutil.py 977 2010-02-09 20:43:13Z robbyd $
@copyright:  2004-2007 Robby Dermody. 2008-Present Castdot, Inc. All Rights Reserved.
@license:    See LICENSE file for more information
"""

#############################
#MODULE DEPENDENCIES
#############################
#General deps
import re
from twisted.python import log

#Project specific deps
from webservice_tools.twisted import errorutil


#############################
#MODULE-LEVEL VARIABLES
#############################


#############################
#MODULE FUNCTIONALITY
#############################
def convertStrToBool(stringData, configDirectiveName='', fatalErrorOnFailure=True):
    """I convert a string variable into it's corresponding boolean variable equivelent. By default,
    everything EXCEPT 'true', 't', '1', or 'yes' (in upper or lower case) is interpreted as False

    @param stringData: The string to interpret

    @param configDirectiveName: If this conversion is being done for the parsing of a configuration directive,
    this parameter should be set to the name of that directive. This will allow me to give more informative
    error output to the user in the event of conversion failure (when fatalErrorOnFailure is set to True as well)

    @param fatalErrorOnFailure: Set to True to cause a fatal error when I can't do the conversion. Otherwise,
    I will generate a ValueError exception.
    
    @return: The boolean equivelent of the passed string
    
    >>> convertStrToBool("true", fatalErrorOnFailure=False)
    True
    >>> convertStrToBool("T", fatalErrorOnFailure=False)
    True
    >>> convertStrToBool("YeS", fatalErrorOnFailure=False)
    True
    >>> convertStrToBool("0", fatalErrorOnFailure=False)
    False
    >>> convertStrToBool("FALSE", fatalErrorOnFailure=False)
    False
    >>> convertStrToBool("f", fatalErrorOnFailure=False)
    False
    >>> convertStrToBool("nO", fatalErrorOnFailure=False)
    False
    
    >>> convertStrToBool("bla", fatalErrorOnFailure=False)
    Traceback (most recent call last):
        ...
    ValueError: Cannot convert string to boolean
    
    >>> convertStrToBool(2, fatalErrorOnFailure=False)
    Traceback (most recent call last):
        ...
    AssertionError

    >>> convertStrToBool(False, fatalErrorOnFailure=False)
    Traceback (most recent call last):
        ...
    AssertionError
    """
    assert(isinstance(stringData, basestring))
    
    stringData = stringData.lower()
    if stringData in ('true', 't', '1', 'yes'):
        return True
    elif stringData in ('false', 'f', '0', 'no'):
        return False
    elif fatalErrorOnFailure:
        if configDirectiveName:
            errorutil.triggerFatalError("Could not parse the configuration directive named \"%s\": "
                "Please set this to \"True\" or \"False\", instead of its current value, \"%s\""
                % (configDirectiveName, stringData))
        else:
            errorutil.triggerFatalError("Could not parse string into boolean value")
    else:
        raise ValueError("Cannot convert string to boolean")


def convertStrToInt(stringData, configDirectiveName='', fatalErrorOnFailure=True, isPortNum=False,
    minVal=-2147483648, maxVal=2147483647):
    """I convert a string variable into it's corresponding integer variable equivelent. 

    @param stringData: The string to interpret

    @param configDirectiveName: If this conversion is being done for the parsing of a configuration directive,
    this parameter should be set to the name of that directive. This will allow me to give more informative
    error output to the user in the event of conversion failure (when fatalErrorOnFailure is set to True as well)
    
    @param isPortNum: Set to true to enforce a numeric range consistent with a port number (1-65535). If
    set to True, the limits specified in the minVal and maxVal parameters will be ignored.
    
    @param minVal: The minimum allowable value for the integer as read in. 

    @param maxVal: The maximum allowable value for the integer as read in. 

    @param fatalErrorOnFailure: Set to True to cause a fatal error when I can't do the conversion. Otherwise,
    I will generate a ValueError exception.
    
    @return: The integer equivelent of the passed string
    
    >>> convertStrToInt("1", fatalErrorOnFailure=False)
    1
    >>> convertStrToInt("-1", fatalErrorOnFailure=False, isPortNum=False)
    -1
    >>> convertStrToInt("101012", fatalErrorOnFailure=False)
    101012
    >>> convertStrToInt("1", fatalErrorOnFailure=False, isPortNum=True)
    1
    >>> convertStrToInt("65534", fatalErrorOnFailure=False, isPortNum=True)
    65534
    >>> convertStrToInt("-1", fatalErrorOnFailure=False, isPortNum=True)
    Traceback (most recent call last):
        ...
    ValueError: "-1" is not a valid port number. It must be between 1 and 65534
    >>> convertStrToInt("65535", fatalErrorOnFailure=False, isPortNum=True)
    Traceback (most recent call last):
        ...
    ValueError: "65535" is not a valid port number. It must be between 1 and 65534
    """
    assert(isinstance(stringData, (str, unicode,)))
    
    try:
        result = int(stringData)
        
        if isPortNum and (result < 1 or result > 65534):
            if fatalErrorOnFailure:
                if configDirectiveName:
                    errorutil.triggerFatalError("Could not parse the configuration directive named \"%s\": "
                        "\"%s\" is not a valid port number (1-65534)" % (configDirectiveName, stringData))
                else:
                    errorutil.triggerFatalError(
                        "\"%s\" is not a valid port number. It must be between 1 and 65534"
                        % stringData)
            else:
                raise ValueError(
                    "\"%s\" is not a valid port number. It must be between 1 and 65534" % stringData)
        elif not isPortNum and result < minVal:
                if configDirectiveName:
                    errorutil.triggerFatalError("Could not parse the configuration directive named \"%s\": "
                        "\"%s\" is less than the allowable minimum (%i)" % (configDirectiveName, stringData, minVal))
                else:
                    errorutil.triggerFatalError(
                        "\"%s\" is not a valid port number. It is less than the allowable minimum (%i)"
                        % stringData, minVal)
        elif not isPortNum and result > maxVal:
                if configDirectiveName:
                    errorutil.triggerFatalError("Could not parse the configuration directive named \"%s\": "
                        "\"%s\" is greater than the allowable maximum (%i)" % (configDirectiveName, stringData, maxVal))
                else:
                    errorutil.triggerFatalError(
                        "\"%s\" is not a valid port number. It is greater than the allowable maximum (%i)"
                        % stringData, maxVal)
        return result
    except ValueError:
        if fatalErrorOnFailure:
            if configDirectiveName:
                errorutil.triggerFatalError("Could not parse the configuration directive named \"%s\": "
                    "Instead of it's current value, \"%s\", it must be a numerical value "
                    "(e.g. no non-digit characters allowed)" % (configDirectiveName, stringData))
            else:
                errorutil.triggerFatalError("Could not parse string \"%s\" into an integer value" % stringData)
        else:
            raise

