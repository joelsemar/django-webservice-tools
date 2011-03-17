import random
import datetime
import passwordpieces
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from webservice_tools.response_util import ResponseObject
from webservice_tools.utils import GeoCode, strToBool, is_valid_email, ReverseGeoCode
from django.http import HttpResponse

def geo(request, response=None):
    if not response:
        response = ResponseObject()
    address = request.GET.get('address')
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    if address:
        get_coords = strToBool(request.GET.get('get_coords', 'True'))
        if hasattr(settings, 'GOOGLE_API_KEY'):
            geo_code = GeoCode(address, apiKey=settings.GOOGLE_API_KEY)
        else:
            #just use the api key in the utils module
            geo_code = GeoCode(address)
        
        if get_coords:
            try:
                response.set(result=geo_code.getCoords())
            except:
                return response.send(errors='Invalid Address')
        else:
            result = geo_code.getResponse()
            if int(result['Status']['code']) == 200:
                response.set(result=geo_code.getResponse())
            else:
                return response.send(errors="Invalid Address")
    elif (lat and lng):
        address = ReverseGeoCode(latlng='%s,%s' %(lat,lng)).getAddress()
        response.set(address=address)
    else:
        return response.send(errors="Pleae provide a lat/lng pair or address")
    return response.send()

handler404_view = lambda request: HttpResponse('{"errors": ["Not Found"], "data": {}, "success": false}', status=404)


def newResetPass(request, response):
    """
    View for the newer api's, doesn't expect .json|.xml in the url, but rather a middleware to provide the 
    response object based on the 'Accept' header
    
    """
    username = request.POST.get('username')
    if not username:
        return response.send(errors='Username or email required', status=404)
    #email address of the first entry in the ADMINS tuple (you should set it to something meaningful)
    try:
        sent_from = settings.ADMINS[0][1]
    except IndexError:
        return response.send(errors="Please supply an ADMIN email address in settings.py", status=500) 
    
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        if is_valid_email(username):
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                return response.send(errors='That user does not appear to exist', status=404)
        else:
            return response.send(errors='That user does not appear to exist', status=404)
    
    if not user.email:
        return response.send(errors="That user has not provided an email address")
    
    newPassword = generateNewPassword()
    user.set_password(newPassword)
    user.save()
    send_mail('Password Reset',
              'The password for the username "%s" has been successfully reset, your new password is "%s",  please change as soon as possible' % (user.username, newPassword),
              '%s' % sent_from, [user.email, ])
    
    request.session['RESET_PASS'] = True
    return response.send()


def resetPass(request, dataFormat='json'):
    """
    Clients working up against the older servers will expect to  call something like /resetpass.json
    This form is now deprecated in favor of an 'accept' header and a middleware that provides the response object
    Just leaving this here so the older apps can provide the dataFormat in the url without error

    """
    return newResetPass(request, ResponseObject(dataFormat=dataFormat))


def amialive(request, response):
    """
    Health check url for ec2 instances
    """
    response.set(datetime=datetime.datetime.utcnow())
    return response.send()

def changePass(request):
    
    response = ResponseObject()
    oldPass = request.POST.get('oldPassword')
    newPass1 = request.POST.get('newPassword1')
    newPass2 = request.POST.get('newPassword2')
    
    if not newPass1 == newPass2 and request.user.check_password(oldPass):
        response.addErrors("Your old password was not entered correctly or your new passwords don't match. Please try again")
        return response.send()
    
    request.user.set_password(newPass1)
    request.user.save()
    return response.send()

    
def generateNewPassword():
    # generates a new password
    return passwordpieces.PASSWORD_WORDS[random.randint(0, len(passwordpieces.PASSWORD_WORDS) - 1)] + \
           passwordpieces.PASSWORD_SPECIAL_CHARACTERS[random.randint(0, len(passwordpieces.PASSWORD_SPECIAL_CHARACTERS) - 1)] + \
           passwordpieces.PASSWORD_WORDS[random.randint(0, len(passwordpieces.PASSWORD_WORDS) - 1)] + \
           passwordpieces.PASSWORD_SPECIAL_CHARACTERS[random.randint(0, len(passwordpieces.PASSWORD_SPECIAL_CHARACTERS) - 1)]
