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
from webservice_tools.apps.social.models import SocialNetwork, UserNetworkCredentials

NETWORK_HTTP_ERROR = "There was a problem reaching %s, please try again."
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
                                                    token=credentials.token, method='POST', params={'status': message})
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
        Attempts to gain permission to a user's data with Twitter, if successful, will return a redirect
        to Twitter's servers, there the user will be prompted to login if necessary, and allow or deny us access.
        API Handler: POST /social/twitter
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
        API Handler: GET /social/twitter
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
        Attempts to gain permission to a user's data with Facebook, if successful, will return a redirect
        to Facebook's servers, there the user will be prompted to login if necessary, and allow or deny us access.
        API Handler POST /social/facebook
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
        This entry point is used by the social networks only, passing our verification string
        We'll take this and exchange for an access_token
        API Handler: GET /social/facebook
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
    
class GetFriendsHandler(BaseHandler):
    allowed_methods = ('GET',)
    
    @login_required
    def read(self, request, response=None):
        """
        Get the list of friends that are in the app given a social network
        API Handler: GET /social/friends
        Params:
            @network: [string] A network that the logged in user has authorized
        """
        
        network = request.GET.get('network')
        
        if not network:
            return response.send(errors="The network is required", status=499)
        
        profile = request.user.get_profile()
        
        if not response:
            response = ResponseObject()