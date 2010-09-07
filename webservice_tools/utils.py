"""
General utils
"""

import types
import re
import xml.sax.handler

JSON_INDENT = 4



def toDict(obj, r=4):
    """ 
    Returns a Dict representation of the given object, replacing object relations with ids
    this is handy for serializing a django model instance
    """
    isDict = isinstance(obj, types.DictType)
    if not any([hasattr(obj, '__dict__'), isDict]) or not r:
        return obj
    
    if isDict:
        generator = obj.iteritems()
        
    else:
        generator = obj.__dict__.iteritems()     
     
    ret = {}
    for k, v in generator:
        if k.startswith('_') or k.endswith('_set'): # ignore 'private' keys
            continue
        elif type(v) is types.ObjectType or hasattr(v, '__dict__'):
            ret[k] = toDict(v, r - 1)
        elif hasattr(v, 'id'):
            ret[k] = v.id
        else:
            ret[k] = v
    
    return ret


def strToBool(str):
    if not isinstance(str, basestring):
        raise TypeError
    
    return str in ['1', 'True', 'true', 't', 'T', 'YES', 'Yes', 'Y', 'y']
        
    
def fromXML(src):
    """
    A simple function to converts XML data into native Python object.
    
    Function taken from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/534109
    
    XML is a popular mean to encode data to share between systems. Despite its ubiquity, there is no straight forward way to translate XML to Python data structure. Traditional API like DOM and SAX often require undue amount of work to access the simplest piece of data.
    
    This method convert XML data into a natural Pythonic data structure. For example:
    
    >>> SAMPLE_XML = \"\"\"<?xml version="1.0" encoding="UTF-8"?>
    ... <address_book>
    ...   <person gender='m'>
    ...     <name>fred</name>
    ...     <phone type='home'>54321</phone>
    ...     <phone type='cell'>12345</phone>
    ...     <note>"A<!-- comment --><![CDATA[ <note>]]>"</note>
    ...   </person>
    ... </address_book>
    ... \"\"\"
    >>> address_book = fromXML(SAMPLE_XML)
    >>> person = address_book.person
    
    To access its data, you can do the following:
    
    person.gender        -> 'm'     # an attribute
    person['gender']     -> 'm'     # alternative dictionary syntax
    person.name          -> 'fred'  # shortcut to a text node
    person.phone[0].type -> 'home'  # multiple elements becomes an list
    person.phone[0].data -> '54321' # use .data to get the text value
    str(person.phone[0]) -> '54321' # alternative syntax for the text value
    person[0]            -> person  # if there are only one <person>, it can still
                                    # be used as if it is a list of 1 element.
    'address' in person  -> False   # test for existence of an attr or child
    person.address       -> None    # non-exist element returns None
    bool(person.address) -> False   # has any 'address' data (attr, child or text)
    person.note          -> '"A <note>"'
    
    This function is inspired by David Mertz' Gnosis objectify utilities. The motivation of writing this recipe in its simplicity. With just 100 lines of code packaged into a single function, it can easily be embedded with other code for ease of distribution.
    """
    
    
    if isinstance(src, unicode):
        #try to take it down to a string if necessary. It may generate an error, but it would throw an error
        # anyhow if we tried to run with a unicode string
        src = str(src)

    non_id_char = re.compile('[^_0-9a-zA-Z]')
    def _name_mangle(name):
        return non_id_char.sub('_', name)

    class DataNode(object):
        def __init__(self):
            self._attrs = {}    # XML attributes and child elements
            self.data = None    # child text data
        def __len__(self):
            # treat single element as a list of 1
            return 1
        def __getitem__(self, key):
            if isinstance(key, basestring):
                return self._attrs.get(key, None)
            else:
                return [self][key]
        def __setitem__(self, key, value):
            self._attrs[key] = value
        def __contains__(self, name):
            return self._attrs.has_key(name)
        def __nonzero__(self):
            return bool(self._attrs or self.data)
        def __getattr__(self, name):
            if name.startswith('__'):
                # need to do this for Python special methods???
                raise AttributeError(name)
            return self._attrs.get(name, None)
        def _add_xml_attr(self, name, value):
            if name in self._attrs:
                # multiple attribute of the same name are represented by a list
                children = self._attrs[name]
                if not isinstance(children, list):
                    children = [children]
                    self._attrs[name] = children
                children.append(value)
            else:
                self._attrs[name] = value
        def __str__(self):
            return self.data or ''
        def __unicode__(self):
            return unicode(self.data) or u''
        def __repr__(self):
            items = sorted(self._attrs.items())
            if self.data:
                items.append(('data', self.data))
            return u'{%s}' % ', '.join([u'%s:%s' % (k, repr(v)) for k, v in items])

    class TreeBuilder(xml.sax.handler.ContentHandler):
        def __init__(self):
            self.stack = []
            self.root = DataNode()
            self.current = self.root
            self.text_parts = []
        def startElement(self, name, attrs):
            self.stack.append((self.current, self.text_parts))
            self.current = DataNode()
            self.text_parts = []
            # xml attributes --> python attributes
            for k, v in attrs.items():
                self.current._add_xml_attr(_name_mangle(k), v)
        def endElement(self, name):
            text = ''.join(self.text_parts).strip()
            if text:
                self.current.data = text
            if self.current._attrs:
                obj = self.current
            else:
                # a text only node is simply represented by the string
                obj = text or ''
            self.current, self.text_parts = self.stack.pop()
            self.current._add_xml_attr(_name_mangle(name), obj)
        def characters(self, content):
            self.text_parts.append(content)

    builder = TreeBuilder()
    if isinstance(src, basestring):
        xml.sax.parseString(src, builder)
    else:
        xml.sax.parse(src, builder)
    return builder.root._attrs.values()[0]




def toXML(obj, objname, nodePrefix='', isCdata=False):
    """
    Converts python data structures into XML
    """
    def getXML_dict(indict, objname=None):
        h = u"<%s>" % objname
        for k, v in indict.items():
            h += toXML(v, k)
        h += u"</%s>" % objname
        return h

    def getXML_list(inlist, objname=None):
        if len(inlist) == 0:
            #return a set of tags to denote an empty list
            #or should we return a single tag like <bla/>?
            return u"<%s></%s>" % (objname, objname)
        
        h = u""
        for i in inlist:
            h += toXML(i, objname)
        return h

    adapt = {
        dict: getXML_dict,
        list: getXML_list,
        tuple: getXML_list,
    }        

    def getXML(obj, objname, nodePrefix='', isCdata=False):
        """
        This function generates XML for any Python object through recursive functions. It is easy to add
        specific handlers for your own object types for more complex output options.
        
        From http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/440595
        """
        if obj == None:
            return u''
        if adapt.has_key(obj.__class__):
            return adapt[obj.__class__](obj, objname)
        else:
            objXML = None
            if hasattr(obj, 'toXML'):
                objXML = obj.toXML(nodePrefix)
                if not objXML: return u''
            if not objXML:
                objXML = unicode(obj)
            if objXML and len(objXML) > 0:
                if isCdata:
                    return u"%s<%s><![CDATA[%s]]></%s>\n" % (nodePrefix, objname, objXML, objname)
                else:
                    return u"%s<%s>%s</%s>\n" % (nodePrefix, objname, objXML, objname)
            else:
                return u"%s<%s/>\n" % (nodePrefix, objname)
    
    return getXML(obj, objname, nodePrefix, isCdata)


def flatten(seq):
    """
    Flattens an array or tuple into a 1d list
    """

    ret = []
    def _flatten(seq):
        for i in seq:
            if isinstance(i, (list, tuple)):
                _flatten(i)
            else:
                ret.append(i)
        return ret
    
    return _flatten(seq)

