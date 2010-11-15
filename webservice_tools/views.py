import random
import passwordpieces
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from webservice_tools.response_util import ResponseObject



def resetPass(request, dataFormat='json'):
    response = ResponseObject(dataFormat=dataFormat)
    username = request.POST.get('username')
    
    #email address of the first entry in the ADMINS tuple (you should set it to something meaningful)
    sent_from = settings.ADMINS[0][1] 
    
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        response.addErrors(errors='That user does not appear to exist', status=404)
        return response.send()
    
    newPassword = generateNewPassword()
    user.set_password(newPassword)
    user.save()
    send_mail('Password Reset',
              'Your password has been successfully reset, your new password is "%s", please change as soon as possible' % newPassword,
              '%s' % sent_from, [user.email, ])
    
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