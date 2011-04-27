"""
General utils
"""
import datetime
import math
import types
import random
import re
import xml.sax.handler
import socket
import urllib
import urllib2
import simplejson
import passwordpieces
import base64
from xml.dom import minidom
from django.utils import encoding
from PIL import Image
from xml.dom.ext import PrettyPrint
from StringIO import StringIO
from piston.resource import Resource as PistonResource
from piston.handler import BaseHandler as PistonBaseHandler, HandlerMetaClass as PistonHandlerMetaClass
from piston.emitters import Emitter, XMLEmitter as PistonXMLEmitter
from webservice_tools.decorators import retry
from django.conf import settings
JSON_INDENT = 4
GOOGLE_API_KEY = "ABQIAAAAfoFQ0utZ24CUH1Mu2CNwjRT2yXp_ZAY8_ufC3CFXhHIE1NvwkxSbhhdGY56wVeZKZ-crGIkLMPghOA"
GOOGLE_API_URL = "http://maps.google.com/maps/geo?output=json&sensor=false&key=%s" 
GOOGLE_REVERSE_URL = 'http://maps.googleapis.com/maps/api/geocode/json?sensor=false&key=%s'

EMAIL_REGEX = "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$"

ZIP_CODE_REGEX = '^[\d]{5}$|^[\d]{5}\-[\d]{4}$'

YAHOO_APPID = "0NYrSEfV34E53zulq2mSDNG2tj6cR5IUlpDpguxqUx6mBs_GDVjIf5OguewjmQ--"
YAHOO_LOCATION_URL = "http://local.yahooapis.com/LocalSearchService/V3/localSearch?"

GOOGLE_QR_CODE_URL = "https://chart.googleapis.com/chart?cht=qr&chs=150x150&(data)s&chld=L|4"
class Resource(PistonResource):
    def determine_emitter(self, request, *args, **kwargs):
        """
        Subclass piston's resource to enable format detection from header
        """
        em = kwargs.pop('emitter_format', None)
        
        accept_header = request.META.get('HTTP_ACCEPT')
        if 'text/xml' in accept_header:
            em = 'xml'
        elif 'application/json' in accept_header:
            em = 'json'
        
        if not em:
            em = request.GET.get('format', 'json')

        return em


class HandlerMetaClass(PistonHandlerMetaClass):
    def __new__(cls, name, bases, attrs):
        
        new_cls = PistonHandlerMetaClass.__new__(cls, name, bases, attrs)
        if hasattr(new_cls, 'model'):
            model = getattr(new_cls, 'model')
            if not new_cls.fields:
                new_cls.fields = tuple(model._meta.get_all_field_names())
        
            new_cls.fields += getattr(new_cls, 'extra_fields', ())
        new_cls.exclude = ()
        return new_cls

class BaseHandler(PistonBaseHandler):
    __metaclass__ = HandlerMetaClass
    
    def format_errors(self, form):
        return [v[0].replace('This field', k.title()) for k, v in form.errors.items()]
    
    def create(self, request, response):
        form = self.form(request.POST)
        if form.is_valid():
            form.save()
            return response.send()
        else:
            return response.send(errors=self.format_errors(form))
    
    def update(self, request, id, response):
        pass
    

class XMLEmitter(PistonXMLEmitter):
    def render(self, request):
        result = super(XMLEmitter, self).render(request)
        if settings.DEBUG:
            result = prettyxml(minidom.parseString(result))
        return result

Emitter.register('xml', XMLEmitter, 'text/xml; charset=utf-8')

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
    
    return str.lower() in ['1', 'true', 't', 'y', 'yes']
        
    
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
                    return u"%s<%s><![CDATA[%s]]></%s>" % (nodePrefix, objname, objXML, objname)
                else:
                    return u"%s<%s>%s</%s>" % (nodePrefix, objname, objXML, objname)
            else:
                return u"%s<%s/>" % (nodePrefix, objname)
    
    return  getXML(obj, objname, nodePrefix, isCdata)



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
    
    if isinstance(seq, tuple):
        return tuple(_flatten(seq))
    
    return _flatten(seq)


class GeoCodeError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)


class GeoCode():
    
    def __init__(self, address, apiKey=GOOGLE_API_KEY):
        self.apiKey = apiKey
        self.query = friendlyURLEncode({'q': address})
    
    def _make_call(self):
        return simplejson.loads(urllib2.urlopen(GOOGLE_API_URL % self.apiKey + '&' + self.query).read())
    
    @retry(exception_raise=GeoCodeError("Invalid Address"))
    def getResponse(self):
        return  self._make_call()
    
    @retry(exception_raise=GeoCodeError("Invalid Address"))
    def getCoords(self):
        response = self._make_call()
        coordinates = response['Placemark'][0]['Point']['coordinates'][0:2]
        return tuple([float(n) for n in coordinates])
            
        
class ReverseGeoCode():      

    def __init__(self, latlng, apiKey=GOOGLE_API_KEY):
        self.apiKey = apiKey
        self.query = friendlyURLEncode({'latlng': latlng})
    
    @retry(exception_raise=GeoCodeError("Invalid Coordinates"))
    def getAddress(self):
        response = simplejson.loads(urllib2.urlopen(GOOGLE_REVERSE_URL % self.apiKey + '&' + self.query).read())
        ret = response['results']
        if not ret:
            raise GeoCodeError('Invalid coordinates')
        return ret
            

class PlacesSearch():
    
    def __init__(self, lat=None, lng=None, query='*', app_id=YAHOO_APPID, **kwargs):
        self.app_id = app_id
        self.query = query
        self.arg_dict = kwargs
        self.arg_dict['query'] = query
        self.arg_dict['output'] = 'json'
        self.arg_dict['appid'] = app_id
        if lat:
            self.arg_dict['latitude'] = lat
        if lng:
            self.arg_dict['longitude'] = lng
        
        
    def fetch(self):
        args = friendlyURLEncode(self.arg_dict)
        return simplejson.loads(urllib2.urlopen(YAHOO_LOCATION_URL + args).read())

            
def generateNewPassword():
    # generates a new password
    return passwordpieces.PASSWORD_WORDS[random.randint(0, len(passwordpieces.PASSWORD_WORDS) - 1)] + \
           passwordpieces.PASSWORD_SPECIAL_CHARACTERS[random.randint(0, len(passwordpieces.PASSWORD_SPECIAL_CHARACTERS) - 1)] + \
           passwordpieces.PASSWORD_WORDS[random.randint(0, len(passwordpieces.PASSWORD_WORDS) - 1)] + \
           passwordpieces.PASSWORD_SPECIAL_CHARACTERS[random.randint(0, len(passwordpieces.PASSWORD_SPECIAL_CHARACTERS) - 1)]
           
           
def friendlyURLEncode(data):
    # makes sure that for every item in your data dictionary that is of unicode type, it is first UTF-8
    # encoded before passing it in to urllib.urlencode()
    data = dict([(k, v.encode('utf-8') if type(v) is types.UnicodeType else v) for (k, v) in data.items()])
    return urllib.urlencode(data)


def truncate(s, length, etc=u"..."):
    """Truncate a string to the given length.
    
    s: The string to truncate
    length: The length to truncate to, INCLUDING the length of etc
    etc: If truncation is necessary, append the value of "etc".
    """
    assert isinstance(s, basestring)
    assert length
    
    if len(s) < length:
        return s
    elif len(etc) >= length:
        return s[:length]
    else:
        return s[:length - len(etc)] + unicode(etc)



def formatPhoneNumber(number):
    m = re.search("\+?1?(\d{3})(\d{3})(\d{4})", number)
    if m:
        return u"(%s) %s-%s" % m.groups()
    return m

def makeAPICall(domain, apiHandler, postData=None, rawPostData=None, queryData=None, userName=None,
                 password=None, secure=False, timeout=5, deserializeAs='json', headers={}):
    """
    @see: L{makeAPICall} 
    """
    assert deserializeAs in ('xml', 'json', 'utf-8', 'skip', None)
    requestType = secure and "https" or "http"
    
    url = "%s://%s/%s" % (requestType, domain, encoding.iri_to_uri(apiHandler))
    
    if queryData:
        queryString = urllib.urlencode(queryData)
        url += "?" + queryString
    
    req = urllib2.Request(url)
    
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    
    if userName is not None and password is not None:
        base64String = base64.encodestring('%s:%s' % (userName, password)).rstrip('\n')
        authheader = 'Basic %s' % base64String
        req.add_header('Authorization', authheader)
            
    defaultTimeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout)
        if postData:
            params = friendlyURLEncode(postData)
            response = urllib2.urlopen(req, params)
        
        elif rawPostData:
            response = urllib2.urlopen(req, rawPostData)
            
        else:
            response = urllib2.urlopen(req)
            
        if deserializeAs == 'json':
            response = simplejson.load(response, encoding='utf-8')
        
        elif deserializeAs == 'xml':
            response = response.read().decode('utf-8')
            response = fromXML(response)
        
        elif deserializeAs == 'utf-8': #skip
            response = response.read().decode('utf-8')
        
        elif deserializeAs == None: # don't decode
            response = response.read()
        
        elif deserializeAs == "skip":
            pass
            
    finally:
        socket.setdefaulttimeout(defaultTimeout)
        
    return response


def is_valid_email(email):
    return re.match(EMAIL_REGEX, email)

"""

The following 2 functions are used to sort ratings based on info found here:
http://www.evanmiller.org/how-not-to-sort-by-average-rating.html
"""
def pnormaldist(qn):
    b = [1.570796288, 0.03706987906, -0.8364353589e-3, -0.2250947176e-3, 0.6841218299e-5, 0.5824238515e-5,
         - 0.104527497e-5, 0.8360937017e-7, -0.3231081277e-8,
         0.3657763036e-10, 0.6936233982e-12]
    
    if (qn < 0.0 or 1.0 < qn or qn == 0.5):
        return 0.0
    
    w1 = qn
    if(qn > 0.5):
        w1 = 1.0 - w1
    
    w3 = -math.log(4.0 * w1 * (1.0 - w1))
    w1 = b[0]
    for i in range(1, 11):
        w1 += b[i] * w3 ** i;
    
    if qn > 0.5:
        return math.sqrt(w1 * w3)
    return - math.sqrt(w1 * w3)


def ci_lower_bound(pos, n, power=0.10):
    """
    pos is the number of positive ratings
    n is the total number of ratings
    power refers to the statistical power: pick 0.10 to have a 95% chance that your lower bound is correct,
     0.05 to have a 97.5% chance, etc.
    """
    if not n:
        return 0
    z = pnormaldist(1 - power / 2)
    phat = 1.0 * pos / n
    
    return (phat + z * z / (2 * n) - z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n)) / (1 + z * z / n)



def prettyxml(node, encoding='utf-8'):
    tmpStream = StringIO()
    PrettyPrint(node, stream=tmpStream, encoding=encoding)
    return tmpStream.getvalue()


def escape_xml(xml):
    return re.sub('&', '&amp;', xml)


def iso_8601_parse(time_string):
    """
    Y-m-dTH:M:S 
    """
    from xml.utils.iso8601 import parse
    return datetime.datetime.fromtimestamp(parse(time_string))


def default_time_parse(time_string):
    """
    Expects times in the format "2011-12-25 18:22"
    Returns None on error
    """
    if not time_string or not isinstance(time_string, basestring):
        return None
    try:
        return datetime.datetime.strptime(time_string, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            return datetime.datetime.strptime(time_string, "%Y-%m-%d %H:%M")
        except ValueError:
            return None

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


first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')
def camel_to_under(name):
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()


def generate_qr_code(data):
    
    fetch_url = GOOGLE_QR_CODE_URL
    post_data = friendlyURLEncode({'chl': data})
    request = urllib2.Request(fetch_url)
    raw = urllib2.urlopen(request, post_data).read()
    return StringIO(raw)
