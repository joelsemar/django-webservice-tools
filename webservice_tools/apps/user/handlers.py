import datetime
import urlparse
import urllib
from piston.handler import BaseHandler
from django.db import transaction
from django.conf import settings
from django.utils.importlib import import_module
from django.http import HttpResponseRedirect, HttpResponse
from webservice_tools import oauth, utils
from django.contrib.auth import authenticate, login, logout
from webservice_tools.decorators import login_required
from webservice_tools.response_util import ResponseObject
from webservice_tools.apps.user.models import SocialNetwork, UserNetworkCredentials

NETWORK_HTTP_ERROR = "There was a problem reaching %s, please try again."
class FormHandler(BaseHandler):
    
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
        

class GenericUserHandler(FormHandler):
    abstract = True
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
    def read(self, request, response):
        """
        Return the details of the User's profile and preferences
        API Handler: GET /user
        """
        user_profile = utils.toDict(request.user.get_profile())
        user_profile['username'] = request.user.username
        
        response.set(user=utils.toDict(user_profile))
        return response.send()
    
    
    @transaction.commit_on_success
    def create(self, request, response):
        """
        Create a new user
        API Handler: POST /user
        Params:
            {{ params }}
        """
        profile_form = self.profile_form(request.POST)
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
        profile_form = self.profile_form(request.PUT, instance=profile)
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


class LoginHandler(BaseHandler):
    allowed_methods = ('POST', 'DELETE', 'GET', 'PUT')
    
    def create(self, request, response):
        """
        Allows the user to login
        API Handler: POST /login
        POST Params
          @username [string] The users's unique identifier, (may be an email address in some cases)
          @password [password] The user's password
        
        """
        #all calls to this handler via '/logout should..
        if request.path.startswith('/logout'):
            return self.read(request)
        
        username = request.POST.get('username') or request.POST.get('email')
        password = request.POST.get('password')
        
        if not all([username, password]):
            return response.send(errors='Username and password are required', status=401)
        
        user = authenticate(username=username, password=password)
        if user:
            profile = user.get_profile()
            login(request, user)
            response.set(user={'username':username, 'id':profile.id, 'email': user.email})
            
            return response.send()
        
        else:
            return response.send(errors='Invalid password/username', status=401)
    
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
     


class SocialNetworkError(Exception):
    pass

class SocialPostHandler(BaseHandler):
    allowed_methods = ('POST',)
    
    @login_required
    def create(self, request, response):
        """
        Post a canned message  to the networks he user has approved
        API Handler:
              POST /user/announce
        PARAMS
             @network_name: 'twitter' | 'facebook'
        """


        user_profile = request.user.get_profile()
         
        text = 'Test post @%s' % datetime.datetime.utcnow()
        network_name = request.POST.get('network_name')
            
        if network_name == 'twitter':
            try:
                twitter_credentials = UserNetworkCredentials.objects.get(network__name='twitter', profile=user_profile)
                self.post_to_twitter(user_profile, twitter_credentials, text)
            except (UserNetworkCredentials.DoesNotExist, SocialNetworkError):
                response.addErrors("Invalid or non existent Twitter credentials")
                response.setStatus(400)
        
        elif network_name == 'facebook':
            try:
                fb_credentials = UserNetworkCredentials.objects.get(network__name='facebook', profile=user_profile)
                self.post_to_facebook(user_profile, fb_credentials, text)
            except UserNetworkCredentials.DoesNotExist:
                response.addErrors("Invalid or non existent Facebook credentials")
                response.setStatus(400)
        
        else:
            return response.send(errors="Please supply a valid network name")

        return response.send()
    
    def post_to_twitter(self, user_profile, credentials, message):
        
        network = credentials.network
        oauthRequest = oauth.makeOauthRequestObject('https://%s/1/statuses/update.json' % network.base_url, network.getCredentials(),
                                                    token=oauth.OAuthToken.from_string(credentials.token), method='POST', params={'status': message})
        oauth.fetchResponse(oauthRequest, network.base_url)
        
    def post_to_facebook(self, user_profile, credentials, message):
        utils.makeAPICall(credentials.network.base_url,
                          '%s/feed' % credentials.uuid,
                           postData={'access_token': credentials.token, 'message': message},
                           secure=True, deserializeAs='skip')   



class TwitterHandler(BaseHandler):
    model = SocialNetwork
    allowed_methods  = ('GET', 'POST')
    @login_required
    def create(self, request, network, response=None):
        """
        Attempts to authorize the user with a service using Oauth v1 (Twitter, LinkedIn) 
        API Handler: POST /twitter
        """
        if not response:
            response = ResponseObject()
            
        try:
            network = SocialNetwork.objects.get(name=network)
        except SocialNetwork.DoesNotExist:
            return response.send(errors='Invalid network', status=404)
        
        #the first step is a an unauthed 'request' token, the provider will not even deal with us until we have that
        # so we build a request, and sign it, 
        tokenRequest = oauth.makeOauthRequestObject(network.getRequestTokenURL(), network.getCredentials(),
                                                    callback=network.getCallBackURL(request), method='POST')
        
        result = oauth.fetchResponse(tokenRequest, network.base_url).read()
        try:
            token = oauth.OAuthToken.from_string(result)
        except KeyError:
            if 'whale' in result:
                return HttpResponse(result)
            return response.send(errors=result)
        
        # save the token to compare to the one provider will send back to us 
        request.session['%s_unauthed_token' % network.name] = token.to_string()   
        
        # we needed the token to form the authorization url for the user to go to
        # so we build the oauth request, sign it, and use that url
        oauthRequest = oauth.makeOauthRequestObject(network.getAuthURL(), network.getCredentials(), token=token)
        
        #finally, redirect the user to the url we've been working so hard on
        request.session['from_url'] = request.META.get('HTTP_REFERER', '/')
        
        return HttpResponseRedirect(oauthRequest.to_url())


    def read(self, request, network, response=None):
        """
        This entry point is used by the social networks only, this is where we direct them  with the oauth_callback
        We'll try and use the oauth_token and verifier they give use to get an access_token
        API Handler: GET /twitter
        GET PARAMS:
          @oauth_token
          @oauth_verifier 
        """
        if not response:
            response = ResponseObject()
            
        profile = request.user.get_profile()
        try:
            network = SocialNetwork.objects.get(name=network)
        except SocialNetwork.DoesNotExist:
            return response.send(errors='Invalid network', status=404)
        
        # The first step is to make sure there is an unauthed_token in the session, and that it matches the one 
        # the provider gave us back
        unauthed_token = request.session.get('%s_unauthed_token' % network.name, None)
        if not unauthed_token:
            return response.send(errors=NETWORK_HTTP_ERROR % network.name)
        request.session['%s_unauthed_token' % network.name] 
        requestToken = oauth.OAuthToken.from_string(unauthed_token)   
        
        # The below ugly hack is brought to you by piston (removes oauth_ keys from request.GET )and urlparse 
        # (places querystring values in lists??)
        if requestToken.key != urlparse.parse_qs(request.META['QUERY_STRING']).get('oauth_token', [None, ])[0]:
            return response.send(errors=NETWORK_HTTP_ERROR % network.name)
        verifier = urlparse.parse_qs(request.META['QUERY_STRING']).get('oauth_verifier', [None, ])[0]
        
        #Now we are building a request, so we can exchange this unauthed token for an access_token
        oauthRequest = oauth.makeOauthRequestObject(network.getAccessTokenURL(), network.getCredentials(),
                                                    token=requestToken, verifier=verifier)
        accessToken = oauth.fetchResponse(oauthRequest, network.base_url).read()
        
        try:
            oauth.OAuthToken.from_string(accessToken)
        except KeyError:
            return response.send(errors=NETWORK_HTTP_ERROR % network.name)

        #store the token in the session and in the db, in the future we will look in the session first, and then
        #the db if that fails
        request.session['%s_access_token' % network.name] = accessToken
        
        UserNetworkCredentials.objects.filter(profile=profile, network=network).delete()
        UserNetworkCredentials.objects.create(access_token=accessToken,
                                              profile=request.user.get_profile(),
                                              network=network)
        
        return response.send()
        

class FacebookHandler(BaseHandler):
    model = SocialNetwork
    allowed_methods = ('GET', 'POST')
    
    @login_required
    def create(self, request, network, response=None):
        """
        Attempts to gain permission to a user's data with networks supporting OAuth2 (Facebook, Gowalla)
        API Handler POST /facebook
        """
        if not response:
            response = ResponseObject()
        try:
            network = SocialNetwork.objects.get(name=network)
        except SocialNetwork.DoesNotExist:
            return response.send(errors='Invalid network', status=404)
        
        request.session['from_url'] = request.META.get('HTTP_REFERER', '/')
        
        args = urllib.urlencode({'client_id' : network.getAppId(),
                                 'redirect_uri': network.getCallBackURL(request),
                                 'scope': network.scope_string})
    
        return HttpResponseRedirect(network.getAuthURL() + '?' + args)


    def read(self, request, network, response=None):
        """
        This is the entrypoint for the social networks to make a request, passing our verification string
        We'll take this and exchange for an access_token
        """
        profile = request.user.get_profile()

        if not response:
            response = ResponseObject()
        try:
            network = SocialNetwork.objects.get(name=network)
        except SocialNetwork.DoesNotExist:
            return response.send(errors='Invalid network', status=404)
        
        verification_string = request.GET.get('code', '')
        if not verification_string:
            # probably the user didn't accept our advances
            return response.send(errors=NETWORK_HTTP_ERROR % network.name)
        
        token_request_args = {'client_id' :  network.getAppId(),
                              'client_secret': network.getSecret(),
                              'redirect_uri': network.getCallBackURL(request),
                              'code' : verification_string}
        
        result = utils.makeAPICall(domain=network.base_url,
                                   apiHandler=network.access_token_path,
                                   queryData=token_request_args,
                                   secure=True, deserializeAs=None)
        
        ret = urlparse.parse_qs(result, keep_blank_values=False)
        access_token = ret['access_token'][0]
        ret = utils.makeAPICall(domain=network.base_url,
                                apiHandler='me?access_token=%s' % access_token,
                                secure=True)
        uuid = ret['id']
        
        UserNetworkCredentials.objects.filter(profile=profile, network=network).delete()
        UserNetworkCredentials.objects.create(access_token=access_token,
                                              profile=profile,
                                              network=network,
                                              uuid=uuid)
        
        return response.send()