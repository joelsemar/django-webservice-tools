""" pydevd_vars deals with variables:
    resolution/conversion to XML.
"""
from pydevd_constants import * #@UnusedWildImport
from types import * #@UnusedWildImport
import sys #@Reimport
import urllib
import threading
import pydevd_resolver
import traceback

#-------------------------------------------------------------------------- defining true and false for earlier versions

try:
    __setFalse = False
except:
    import __builtin__
    __builtin__.True = 1
    __builtin__.False = 0

#------------------------------------------------------------------------------------------------------ class for errors

class VariableError(RuntimeError):pass
class FrameNotFoundError(RuntimeError):pass


#------------------------------------------------------------------------------------------------------ resolvers in map

if not sys.platform.startswith("java"):
    typeMap = [
        #None means that it should not be treated as a compound variable
        
        #isintance does not accept a tuple on some versions of python, so, we must declare it expanded
        (NoneType, None,),
        (IntType, None),
        (LongType, None),
        (FloatType, None),
        (ComplexType, None),
        (StringType, None),
        (UnicodeType, None),
        (TupleType, pydevd_resolver.tupleResolver),
        (ListType, pydevd_resolver.tupleResolver),
        (DictType, pydevd_resolver.dictResolver),
    ]
    
    try:
        typeMap.append((set, pydevd_resolver.setResolver))
        typeMap.append((frozenset, pydevd_resolver.setResolver))
    except:
        pass #not available on all python versions
    
else: #platform is java   
    from org.python import core #@UnresolvedImport
    typeMap = [
        (core.PyNone, None),
        (core.PyInteger, None),
        (core.PyLong, None),
        (core.PyFloat, None),
        (core.PyComplex, None),
        (core.PyString, None),
        (core.PyTuple, pydevd_resolver.tupleResolver),
        (core.PyList, pydevd_resolver.tupleResolver),
        (core.PyDictionary, pydevd_resolver.dictResolver),
        (core.PyStringMap, pydevd_resolver.dictResolver),
        (core.PyJavaInstance, pydevd_resolver.instanceResolver),
    ]


def getType(o):
    """ returns a triple (typeObject, typeString, resolver
        resolver != None means that variable is a container, 
        and should be displayed as a hierarchy.
        Use the resolver to get its attributes.
        
        All container objects should have a resolver.
    """    
    
    try:
        type_object = type(o)
        type_name = type_object.__name__
    except:
        #This happens for org.python.core.InitModule
        return 'Unable to get Type', 'Unable to get Type', None
        
    try:        
        
        if type_name =='org.python.core.PyJavaInstance':
            return (type_object, type_name, pydevd_resolver.instanceResolver)
        
        if type_name =='org.python.core.PyArray':
            return (type_object, type_name, pydevd_resolver.jyArrayResolver)    
        
        for t in typeMap:            
            if isinstance(o, t[0]):                
                return (type_object, type_name, t[1])
    except:
        traceback.print_exc()
        
    #no match return default        
    return (type_object, type_name, pydevd_resolver.defaultResolver)


def makeValidXmlValue(s):
    return s.replace('<', '&lt;').replace('>', '&gt;')


def varToXML(v, name):
    """ single variable or dictionary to xml representation """
    type, typeName, resolver = getType(v)    
    
    try:
        if hasattr(v, '__class__'):
            try:
                cName = str(v.__class__)
                if cName.find('.') != -1:
                    cName = cName.split('.')[-1]
                
                elif cName.find("'") != -1: #does not have '.' (could be something like <type 'int'>)
                    cName = cName[cName.index("'")+1:]
                    
                if cName.endswith("'>"):
                    cName = cName[:-2]
            except:
                cName = str(v.__class__)
            value = '%s: %s' % (cName, v)
        else:
            value = str(v)
    except:
        try:
            value = `v`
        except:
            value = 'Unable to get repr for %s' % v.__class__
    
    xml = '<var name="%s" type="%s"' % (name, typeName)
    
    if value: 
        #cannot be too big... communication may not handle it.
        if len(value) >  MAXIMUM_VARIABLE_REPRESENTATION_SIZE:
            value = value[0:MAXIMUM_VARIABLE_REPRESENTATION_SIZE]
            value += '...'

        #fix to work with unicode values
        try:
            if isinstance(value, unicode):
                value = value.encode('utf-8')
        except TypeError: #in java, unicode is a function
            pass
            
        xmlValue = ' value="%s"' % (makeValidXmlValue(urllib.quote(value, '/>_= \t')))
    else:
        xmlValue = ''
        
    if resolver is not None: 
        xmlCont = ' isContainer="True"'
    else:
        xmlCont = ''
        
    return ''.join((xml, xmlValue, xmlCont, ' />\n'))
    

if USE_PSYCO_OPTIMIZATION:
    try:
        import psyco
        varToXML = psyco.proxy(varToXML)
    except ImportError:
        if hasattr(sys, 'exc_clear'): #jython does not have it
            sys.exc_clear() #don't keep the traceback -- clients don't want to see it


def frameVarsToXML(frame):
    """ dumps frame variables to XML
    <var name="var_name" scope="local" type="type" value="value"/>
    """    
    xml = ""
    keys = frame.f_locals.keys()
    keys.sort()    
    for k in keys:
        try:            
            v = frame.f_locals[k]            
            xml += varToXML(v, str(k))
        except Exception, e:
            traceback.print_exc()
            print >>sys.stderr, "unexpected error, recovered safely", str(e)
    return xml

def iterFrames(initialFrame):
    '''NO-YIELD VERSION: Iterates through all the frames starting at the specified frame (which will be the first returned item)'''
    #cannot use yield
    frames = []
    
    while initialFrame is not None:
        frames.append(initialFrame)
        initialFrame = initialFrame.f_back
        
    return frames

def dumpFrames(thread_id):
    print 'dumping frames'
    if thread_id != GetThreadId(threading.currentThread()) : 
        raise VariableError("findFrame: must execute on same thread")
        
    curFrame = GetFrame()
    for frame in iterFrames(curFrame):
        print id(frame)
    
def findFrame(thread_id, frame_id):
    """ returns a frame on the thread that has a given frame_id """
    if thread_id != GetThreadId(threading.currentThread()) : 
        raise VariableError("findFrame: must execute on same thread")

    curFrame = GetFrame()
    if frame_id == "*": 
        return curFrame # any frame is specified with "*"
    
    frameFound = None
    lookingFor = int(frame_id)
    
    for frame in iterFrames(curFrame):
        if lookingFor == id(frame):
            frameFound = frame
            del frame
            break
        
        del frame
    
    #for some reason unknown to me, python was holding a reference to the frame
    #if we didn't explicitly add those deletes (even after ending this context)
    #so, those dels are here for a reason (but still doesn't seem to fix everything)
    del curFrame
        
    if frameFound is None: 
        msgFrames = ''
        i = 0
        
        for frame in iterFrames(GetFrame()):
            i += 1
            msgFrames += str(id(frame))
            if i % 5 == 0:
                msgFrames += '\n'
            else:
                msgFrames += '  -  '
                
        errMsg = '''findFrame: frame not found.
Looking for thread_id:%s, frame_id:%s
Current     thread_id:%s, available frames:
%s
''' % (thread_id, lookingFor, GetThreadId(threading.currentThread()), msgFrames)

        raise FrameNotFoundError(errMsg)
    
    return frameFound

def resolveCompoundVariable(thread_id, frame_id, scope, attrs):
    """ returns the value of the compound variable as a dictionary"""    
    frame = findFrame(thread_id, frame_id)    
    attrList = attrs.split('\t')
    if scope == "GLOBAL":        
        var = frame.f_globals
        del attrList[0] # globals are special, and they get a single dummy unused attribute
    else:
        var = frame.f_locals

    for k in attrList:
        type, _typeName, resolver = getType(var)              
        var = resolver.resolve(var, k)
    
    try:        
        type, _typeName, resolver = getType(var)        
        return resolver.getDictionary(var)
    except:
        traceback.print_exc()
    
def evaluateExpression(thread_id, frame_id, expression, doExec):
    '''returns the result of the evaluated expression
    @param doExec: determines if we should do an exec or an eval
    '''
    frame = findFrame(thread_id, frame_id)
    
    expression = expression.replace('@LINE@', '\n')
    if doExec:
        try:
            #try to make it an eval (if it is an eval we can print it, otherwise we'll exec it and 
            #it will have whatever the user actually did)
            compiled = compile(expression, '<string>', 'eval')
        except:
            exec expression in frame.f_globals, frame.f_locals
        else:
            result = eval(compiled, frame.f_globals, frame.f_locals)
            print result
        return 
    
    else:
        result = None    
        try:
            result = eval(expression, frame.f_globals, frame.f_locals)
        except Exception, e:
            result = str(e)
        return result
    
def changeAttrExpression(thread_id, frame_id, attr, expression):
    '''Changes some attribute in a given frame.
    @note: it will not (currently) work if we're not in the topmost frame (that's a python
    deficiency -- and it appears that there is no way of making it currently work --
    will probably need some change to the python internals)
    '''
    frame = findFrame(thread_id, frame_id)
    
    try:
        expression = expression.replace('@LINE@', '\n')
#tests (needs proposed patch in python accepted)
#        if hasattr(frame, 'savelocals'):
#            if attr in frame.f_locals:
#                frame.f_locals[attr] = eval(expression, frame.f_globals, frame.f_locals)
#                frame.savelocals()
#                return
#                
#            elif attr in frame.f_globals:
#                frame.f_globals[attr] = eval(expression, frame.f_globals, frame.f_locals)
#                return
            
            
        if attr[:7] == "Globals":
            attr = attr[8:]
            if attr in frame.f_globals:
                frame.f_globals[attr] = eval(expression, frame.f_globals, frame.f_locals)
        else:
            #default way (only works for changing it in the topmost frame)
            exec '%s=%s' % (attr, expression) in frame.f_globals, frame.f_locals
            
            
    except Exception, e:
        traceback.print_exc()
    




