import sys
from webservice_tools.utils import BaseHandler
from django.db import transaction
from django.conf import settings
from django.utils.importlib import import_module
from webservice_tools import utils
from django.contrib.auth import authenticate, login, logout
from webservice_tools.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
NETWORK_HTTP_ERROR = "There was a problem reaching %s, please try again."


class UnusedUserHandler(utils.PistonBaseHandler):
    model = User
    fields = ('id', 'username', 'first_name', 'last_name', 'last_login', 'email', 'is_staff')

class GenericUserHandler(utils.BaseHandler):
    allowed_methods = ('POST', 'GET', 'PUT')
    
    def __init__(self):
        for app in settings.INSTALLED_APPS:
            try:
                forms = import_module('%s.forms' % app)
            except:
                continue
            if hasattr(forms, 'UserForm'):
                self.user_form = forms.UserForm
            if hasattr(forms, 'UserProfileForm'):
                self.profile_form = forms.UserProfileForm
    
    @login_required
    def read(self, request, response=None):
        """
        Return the details of the User's profile and preferences
        API Handler: GET /user
        """
        
        profile = request.user.get_profile()
        response.set(profile=profile)
        return response.send()
    
    @transaction.commit_on_success
    def create(self, request, response):
        """
        Create a new user
        API Handler: POST /user
        Params:
            {{ params }}
        """
        profile_form = self.profile_form(request.POST, request.FILES)
        user_form = self.user_form(request.POST)
        if user_form.is_valid():
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            user.save()
        
        else:
            response.addErrors(self.format_errors(user_form))
        
        if profile_form.is_valid():
            profile = profile_form.save(commit=False)
        
        else:
            response.addErrors(self.format_errors(profile_form))
        
        if response._errors:
            transaction.rollback()
            return response.send()
        
        profile.user = user
        profile.save()
        profile.create_callback()
        user = authenticate(username=user_form.cleaned_data['username'], password=user_form.cleaned_data['password'])
        
        if user:
            login(request, user)
            response.set(user={'username':user.username, 'id' :profile.id})
            response.setStatus(201)
            return response.send()
        
        transaction.rollback()
        return response.send(errors='User creation failed', status=500)

    @transaction.commit_on_success
    def update(self, request, response):
        """
        Update the logged in user
        API handler: PUT /user
        """
        profile = request.user.get_profile()
        profile_form = self.profile_form(request.PUT, request.FILES, instance=profile)
        user_form = self.user_form(request.PUT, instance=request.user)
        
        
        if profile_form.is_valid():
            profile_form.save()
        else:
            response.addErrors(self.format_errors(profile_form))
        
        if user_form.is_valid():
            user_form.save()
        else:
            response.addErrors(self.format_errors(user_form))
        
        if response._errors:
            transaction.rollback()
            return response.send()
        
        if user_form.cleaned_data.get('password'):
            request.user.set_password(user_form.cleaned_data.get('password'))
        
        profile.update_callback()
        return response.send()


class LoginHandler(utils.BaseHandler):
    allowed_methods = ('POST', 'DELETE', 'GET', 'PUT')
    
    def create(self, request, response):
        """
        Allows the user to login
        API Handler: POST /login
        
        POST Params:
           @username [string] The users's unique identifier, (may be an email address in some cases)
           @password [password] The user's password
           @email [email] alternative for username where applicable
        
        Returns:
            @username [string] users username
            @id [id] id of the user
            @email [email] user's email address
            @errors [list] insufficient_credentials, invalid_credentials
        """
        #all calls to this handler via '/logout should..
        if request.path.startswith('/logout'):
            return self.read(request)
        
        username = request.POST.get('username', '').lower() or request.POST.get('email', '').lower()
        password = request.POST.get('password')
        
        if not all([username, password]):
            return response.send(errors='insufficient_credentials', status=401)
        
        user = authenticate(username=username, password=password)
        if user:
            single_session = getattr(settings, "SINGLE_SESSION", False)
            if single_session:
                [s.delete() for s in Session.objects.all() if s.get_decoded().get('_auth_user_id') == user.id]
            profile = user.get_profile()
            login(request, user)
            response.set(user={'username':username, 'id':profile.id, 'email': user.email})
            
            return response.send()
        
        else:
            return response.send(errors='invalid_credentials', status=401)
    
    def read(self, request, response):
        """
        Logout
        API Handler: GET /logout
        """
        logout(request)
        return response.send()
        
    
    def update(self, request, response):
        """
        Logout
        API Handler: PUT /logout
        PARAMS:
           device_token: (optional)
        """
        return self.read(request, response)
    
    def delete(self, request, response):
        """
        Logout
        API Handler: DELETE /logout
        """
        return self.read(request, response)
     

#ALL DEFINITION EOF
module_name = globals().get('__name__')
handlers = sys.modules[module_name]
handlers._all_ = []
for handler_name in dir():
    m = getattr(handlers, handler_name)
    if type(m) == type(BaseHandler):
        handlers._all_.append(handler_name)