# -*- coding: utf-8 -*-
"""
Paypal related logic

"""

#############################
#MODULE DEPENDENCIES
#############################
#General deps
import sys
import urllib
import urllib2
import uuid
from webservice_tools import utils
#Project specific deps



#############################
#MODULE-LEVEL VARIABLES
#############################
API_NAMESPACE = 'paypal' #must be unique in all IBL-API namespaces


#############################
#MODULE FUNCTIONALITY
#############################
class PayPal:
    """ #PayPal utility class
    
    ## see https://www.paypal.com/IntegrationCenter/ic_nvp.html
    ## and
    ## https://www.paypal.com/en_US/ebook/PP_NVPAPI_DeveloperGuide/index.html
    ## for more information.
    
    # Credits: Content merged in from two sources:
    # Source #1:
    # by Mike Atlas / LowSingle.com / MassWrestling.com, September 2007
    # No License Expressed. Feel free to distribute, modify, 
    #  and use in any open or closed source project without credit to the author
    # Source #2:
    # PayFlowPro 0.1dev - http://pypi.python.org/pypi/PyFlowPro/0.1dev
    # Under the MIT license.
    #Further modified  to work with the PayFlow Pro API
    
    # Example usage: ===============
    #    paypal = util.PayPal('sandbox', user, password, signature)
    #    ppToken = paypal.set_express_checkout(100)
    #    expressToken = paypal.get_express_checkout_details(ppToken)
    #    HttpResponseRedirect(paypal.get_express_checkout_url(expressToken)) ## django specific http redirect call for payment
    """
    _apiMode = '' 
    _user = ''
    _password = ''
    _siteDomain = ''
    API_ENDPOINT = ""
    TIMEOUT = 45 #recommended value in docs
    
    #Paypal-related constants
    PAYPAL_NVP_API_URL_SANDBOX = 'https://pilot-payflowpro.paypal.com'
    PAYPAL_NVP_API_HOSTADDRESS_SANDBOX = 'pilot-payflowpro.paypal.com'
    PAYPAL_NVP_API_URL_LIVE = 'https://payflowpro.paypal.com'
    PAYPAL_NVP_API_HOSTADDRESS_LIVE = 'payflowpro.paypal.com'
    PAYPAL_EXPRESS_CHECKOUT_URL_SANDBOX = 'https://www.sandbox.paypal.com/webscr&cmd=%20express-checkout&token='
    PAYPAL_EXPRESS_CHECKOUT_URL_LIVE = 'https://www.paypal.com/webscr&cmd=%20express-checkout&token='
    PAYPAL_PAY_URL_SANDBOX = 'https://api-3t.sandbox.paypal.com/nvp'
    PAYPAL_PAY_URL_LIVE = 'https://api-3t.paypal.com/nvp'
    
    
    def __init__(self, apiMode, user, password, merchantUser=None, siteDomain=None, signature=None):
        if apiMode == 'sandbox':
            self._apiMode = 'sandbox'
        elif apiMode == 'live':
            self._apiMode = 'live'
        else:
            raise Exception("Invalid value for apiMode")
        self._user = str(user)
        self._merchantUser = merchantUser and str(merchantUser) or str(user) 
        self._password = str(password)
        self._siteDomain = siteDomain and str(siteDomain) or ''
        self._signature = signature and str(signature) or ''
        self.PAYFLOW_STANDARD_HEADERS = {
            'Connection': 'close',
            'Content-Type': 'text/namevalue',
            'Host': self.API_ENDPOINT,
            #'X-VPS-INTEGRATION-PRODUCT': 'PyFlowPro',
            #'X-VPS-INTEGRATION-VERSION': '1',
            'X-VPS-VIT-OS-NAME': sys.platform,
            'X-VPS-CLIENT-TIMEOUT': str(self.TIMEOUT), # Doc says to do this
            #'X-VPS-Timeout': str(self.timeout), # Example says to do this
        }    


    def _make_request(self, headers, params):
        #paramsString = urllib.urlencode(params)
        #paramsString = paramsString.replace('+', ' ')
        #print "request params", params
        
        req = urllib2.Request(url=self.API_ENDPOINT, data=str(params), headers=headers)
        try:
            response = urllib2.urlopen(req)
            data = response.read()
            response.close()
        except urllib2.URLError:
            data = "RESULT=100&RESPMSG=FAILED_TO_REACH_API_ENDPOINT" 
        
        response.close()
        return data
        
        
    def _make_response_dict(self, responseData):
        """Out of the paypal response, makes a python dict. All entries are forced down to lowercase, and
        all text is unquoted.
        """
        responseTokens = {}
        for token in responseData.split('&'):
            responseTokens[(token.split("=")[0]).lower()] = (token.split("=")[1]).lower()
        for key in responseTokens.keys():
            responseTokens[key] = urllib.unquote(responseTokens[key])
        return responseTokens
        

    # API METHODS
    #TODO: don't allow & and = symbols to be used in any parameters we send to the server!
    def set_express_checkout(self, amount, userLocaleCode='US'):
        """
        @return: The TOKEN value from the result of the call
        """
        assert isinstance(amount, str)
        assert isinstance(userLocaleCode, str)
        
        headers = { 'X-VPS-REQUEST-ID': uuid.uuid4(), }
        headers.update(self.PAYFLOW_STANDARD_HEADERS) 
        params = NvpDict(
            #Base parameters
            TRXTYPE='S',
            TENDER='P', #P for paypal, C for credit card
            PARTNER='PayPal',
            VENDOR=self._merchantUser, #same as user for a single user account
            USER=self._user,
            PWD=self._password,
            #Other parameters
            ACTION='S',
            AMT=amount,
            RETURNURL='https://%s/myAccount/buyCredits/payPalConfirm' % self._siteDomain,
            CANCELURL='http://%s/myAccount/buyCredits/payPalCancelled/' % self._siteDomain,
            NOSHIPPING='1',
            LOCALECODE=userLocaleCode,
        )
        
        responseData = self._make_request(headers, params)
        response = self._make_response_dict(responseData)
        assert 'token' in response
        return response['token']
    
    
    def get_express_checkout_details(self, token):
        assert isinstance(token, str)
        
        headers = { 'X-VPS-REQUEST-ID': uuid.uuid4(), }
        params = NvpDict(
            #Base parameters
            TRXTYPE='S',
            TENDER='P', #P for paypal, C for credit card
            PARTNER='PayPal',
            VENDOR=self._merchantUser, #same as user for a single user account
            USER=self._user,
            PWD=self._password,
            #Other parameters
            ACTION='G',
            TOKEN=token,
        )

        responseData = self._make_request(headers, params)
        return self._make_response_dict(responseData)
    
    
    def do_express_checkout_payment(self, token, payerID, amount):
        assert isinstance(token, str)
        assert isinstance(payerID, str)
        assert isinstance(amount, str)
        
        headers = { 'X-VPS-REQUEST-ID': uuid.uuid4(), }
        params = NvpDict(
            #Base parameters
            TRXTYPE='S',
            TENDER='P', #P for paypal, C for credit card
            PARTNER='PayPal',
            VENDOR=self._merchantUser, #same as user for a single user account
            USER=self._user,
            PWD=self._password,
            #Other parameters
            ACTION='D',
            TOKEN=token,
            PAYERID=payerID,
            AMT=amount,
            ORDERDESC=utils.truncate('%s SERVICE' % self._siteDomain, 127, etc=''),
            SHIPTOSTREET='', #required?
            SHIPTOCITY='', #required?
            SHIPTOCOUNTRY='US', #required?
            L_DESCn=utils.truncate('%s SERVICE' % self._siteDomain, 127, etc=''),
        )

        responseData = self._make_request(headers, params)
        return self._make_response_dict(responseData)
        
        
    def get_express_checkout_url(self, paypalToken):
        if self._apiMode == 'sandbox':
            return self.PAYPAL_EXPRESS_CHECKOUT_URL_SANDBOX + paypalToken
        else:
            return self.PAYPAL_EXPRESS_CHECKOUT_URL_LIVE + paypalToken


    def do_direct_payment(self, amount, acct, expMo, expYear, firstName='', lastName='', ccType='', street1='',
    street2='', city='', state='', postalCode='', countryCode='', cvv2=None):
        
        assert isinstance(amount, str)
        assert isinstance(acct, str)
        assert isinstance(expMo, str)
        assert isinstance(expYear, str)
        assert isinstance(firstName, str)
        assert isinstance(lastName, str)
        assert isinstance(ccType, str)
        assert isinstance(street1, str)
        assert isinstance(street2, str)
        assert isinstance(city, str)
        assert isinstance(state, str)
        assert isinstance(postalCode, str)
        assert isinstance(countryCode, str)
                
        if self._apiMode == 'sandbox':
            self.API_ENDPOINT = self.PAYPAL_NVP_API_URL_SANDBOX
        elif self._apiMode == 'live':
            self.API_ENDPOINT = self.PAYPAL_NVP_API_URL_LIVE
            
        headers = { 'X-VPS-REQUEST-ID': uuid.uuid4(), }
        
        params = NvpDict(
            #Required parameters
            TRXTYPE='S',
            TENDER='C', #P for paypal, C for credit card
            PARTNER='PayPal',
            VENDOR=self._merchantUser, #same as user for a single user account
            USER=self._user,
            PWD=self._password,
            ACCT=acct,
            AMT=amount,
            #^ use userID instead of username b/c username can have underscores and this is an alphanumeric field only
            CURRENCY='USD',
            EXPDATE=expMo + expYear, #like 0308 for March, 2008
            NAME=str(utils.truncate(firstName + ' ' + lastName, 30, etc='')),
            STREET=str(utils.truncate(street1 + street2, 30, etc='')),
            CITY=city,
            STATE=state,
            ZIP=postalCode,
            BILLTOCOUNTRY=countryCode,
        )
        
        # cvv2 is not required, if it is passed then use it
        if cvv2:
            params['CVV2'] = cvv2
            
        responseData = self._make_request(headers, params)
        return self._make_response_dict(responseData)


    def do_reference_payment(self, amount, pnRef):
        assert isinstance(amount, str)
        assert isinstance(pnRef, str)
        
        if self._apiMode == 'sandbox':
            self.API_ENDPOINT = self.PAYPAL_NVP_API_URL_SANDBOX
        elif self._apiMode == 'live':
            self.API_ENDPOINT = self.PAYPAL_NVP_API_URL_LIVE
            
        headers = { 'X-VPS-REQUEST-ID': uuid.uuid4(), }
        params = NvpDict(
            #Required parameters
            TRXTYPE='S',
            TENDER='C', #P for paypal, C for credit card
            PARTNER='PayPal',
            VENDOR=self._merchantUser, #same as user for a single user account
            USER=self._user,
            PWD=self._password,
            ORIGID=pnRef,
            AMT=amount,
            #^ use userID instead of username b/c username can have underscores and this is an alphanumeric field only
        )
        responseData = self._make_request(headers, params)
        return self._make_response_dict(responseData)


    def do_mass_payment(self, paymentList):
        
        assert len(paymentList)
        
        if self._apiMode == 'sandbox':
            self.API_ENDPOINT = self.PAYPAL_PAY_URL_SANDBOX
        elif self._apiMode == 'live':
            self.API_ENDPOINT = self.PAYPAL_PAY_URL_LIVE

        params = {
            'METHOD': 'MassPay',
            'CURRENCYCODE': 'USD',
            'VERSION': '51.0',
            'USER': self._user,
            'PWD': self._password,
            'SIGNATURE': self._signature
                  }

        paymentCount = 0
        for payment in paymentList:
            params['L_AMT%s' % (paymentCount)] = payment['amount']
            params['L_EMAIL%s' % (paymentCount)] = payment['email']
        
        req = urllib2.Request(self.API_ENDPOINT)
        params = utils.friendlyURLEncode(params)
        responseData = urllib2.urlopen(req, params)
           
        import cgi
        return cgi.parse_qs(responseData.read())
        
        
        
class NvpDict(dict):
    """NvpDict, a specialized dictionary for Payflow Pro's Name-Value-Pair
    (NVP) format.
    
    License terms for NvpDict class, along with the _to_dict function (both in this file):
    #  Author:  Matthew Scott <gldnspud at gmail com>
    # Home Page: http://code.3purple.com/pyflowpro/
    # License: MIT 
    
    Copyright (c) 2007(??) Matthew Scott <gldnspud at gmail com>
    
    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:
    
    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.
    
    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
    THE SOFTWARE.
    """
    def __init__(self, *args, **kw):
        super(NvpDict, self).__init__()
        # >0 positional args with >0 keyword args is ambiguous.
        if len(args) > 0 and len(kw) > 0:
            raise TypeError(
                'Provide either positional or keyword arguments, not both.')
        # >1 positional args is ambiguous.
        if len(args) > 1:
            raise TypeError('Provide only one positional argument.')
        if len(args) == 1:
            # Positional arg: convert to a dictionary.
            kw = _to_dict(args[0])
        self.update(kw)

    def __getitem__(self, key):
        return super(NvpDict, self).__getitem__(key.lower())

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise KeyError('Key must be a string.')
        if not isinstance(value, str):
            raise KeyError('Value must be a string.')
        if '\n' in key:
            raise KeyError('Key must not contain newline.')
        if '"' in key:
            raise KeyError('Key must not have double quote.')
        if '\n' in value:
            raise ValueError('Value must not contain newline.')
        if '"' in value:
            raise ValueError('Value must not contain double quote.')
        super(NvpDict, self).__setitem__(key.lower(), value)

    def __str__(self):
        args = []
        for key, value in self.items():
            key = '%s[%d]' % (key.upper(), len(value))
            args.append('%s=%s' % (key, value))
        args.sort()
        return '&'.join(args)

    def copy(self):
        return NvpDict(**self)

    def update(self, other):
        # Update item-by-item so that __setitem__ rules are enforced.
        for key, value in other.iteritems():
            self[key] = value
        

NAME, LEN, VALUE, RESET = range(4)


def _to_dict(s):
    """
    Return a dictionary version of the parmlist string `s`.
    
    See license information for NvpDict.
    """
    # Not a very clever implementation, but used in production for a
    # couple of years, and not out to be a speed demon anyway.  Just a
    # simple state machine.  If anyone takes the time to implement a
    # regex version, please let me know!  -mscott
    result = {}
    state = NAME
    cur_name = ''
    cur_len_str = ''
    cur_len = 0
    cur_value = ''
    processed = ''
    end = len(s) - 1
    for (i, c) in enumerate(s):
        processed += c
        if state is NAME:
            if c.isalnum():
                cur_name += c
            elif c in '[]':
                state = LEN
            elif c is '=':
                state = VALUE
            else:
                raise ValueError('Error parsing string into values at %r in %r.'
                                 % (processed, s))
        elif state is LEN:
            if c.isdigit():
                cur_len_str += c
            elif c is ']':
                state = NAME
            else:
                raise ValueError('Error parsing string into values at %r in %r.'
                                 % (processed, s))
        elif state is VALUE:
            if cur_len_str:
                cur_len = int(cur_len_str)
                cur_len_str = ''
            if cur_len:
                cur_value += c
                cur_len -= 1
                if not cur_len:
                    state = RESET
                    if i == end:
                        result[cur_name] = cur_value
                    continue
            elif c is '&':
                state = RESET
            else:
                cur_value += c
        if state is RESET or i == end:
            result[cur_name] = cur_value
            cur_name = ''
            cur_len_str = ''
            cur_len = 0
            cur_value = ''
            if state is RESET:
                state = NAME
    return result

