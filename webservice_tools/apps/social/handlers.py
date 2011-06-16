import datetime
import urlparse
import urllib
import simplejson
from urllib2 import HTTPError
from django.db import transaction, models
from django.conf import settings
from django.utils.importlib import import_module
from django.http import HttpResponseRedirect, HttpResponse
from webservice_tools import oauth, utils
from webservice_tools.utils import BaseHandler
from django.contrib.auth import authenticate, login, logout
from webservice_tools.decorators import login_required
from webservice_tools.response_util import ResponseObject
from webservice_tools.apps.social.models import SocialNetwork, UserNetworkCredentials
app_label, model_name = settings.AUTH_PROFILE_MODULE.split('.')
PROFILE_MODEL = models.get_model(app_label, model_name)
NETWORK_HTTP_ERROR = "There was a problem reaching %s, please try again."

class SocialNetworkError(Exception):
    pass


class SocialFriendHandler(BaseHandler):
    allowed_methods = ('GET',)
    
    @login_required
    def read(self, request, response):
        """
        Get the list of friends from a social network for a user that has registered us with that network
        API Handler: GET /social/friends
        Params:
          @network [string] {twitter|facebook|linkedin}
        """
        network = request.GET.get('network')
        extra = request.GET.get('extra')
        profile = request.user.get_profile()
        
        try:
            network = SocialNetwork.objects.get(name=network)
        except SocialNetwork.DoesNotExist:
            return response.send(errors='Invalid network', status=404)        
        
        try:
            credentials = UserNetworkCredentials.objects.get(profile=profile, network=network)
        except UserNetworkCredentials.DoesNotExist:
            return response.send(errors='Either %s does not exist or we do not have credentials for that user.' % network.name)
        
        
        try:
            #Use the name of the network to call the helper function
            friend_social_ids = getattr(self, network.name)(profile, network, credentials)
        except HTTPError:
            return response.send(errors=NETWORK_HTTP_ERROR % network.name)
        
        social_friends_credentials = UserNetworkCredentials.objects.filter(network=network,
                                                                           uuid__in=friend_social_ids)
        
        results = [{'id':cred.profile.id,
                    'name_in_network':cred.name_in_network,
                    'username':cred.profile.user.username} for cred in social_friends_credentials]
        
        response.set(results=results)
        
        return response.send()
        
    def facebook(self, profile, network, credentials):
        friends = utils.makeAPICall(network.base_url,
                                 'me/friends',
                                 queryData={'access_token': credentials.token},
                                 secure=True)
        
        return [x['id'] for x in friends['data']] 
        
    def twitter(self, profile, network, credentials):
        oauthRequest = oauth.makeOauthRequestObject('https://%s/1/statuses/friends.json' % network.base_url,
                                                    network.getCredentials(),
                                                    token=oauth.OAuthToken.from_string(credentials.token))
        ret = oauth.fetchResponse(oauthRequest, network.base_url).read()
        friends = simplejson.loads(ret)
        return [x['id'] for x in friends]
    
    def linkedin(self, profile, network, credentials):
        oauthRequest = oauth.makeOauthRequestObject('https://%s/v1/people/~/connections' % network.base_url,
                                                    network.getCredentials(), method='GET',
                                                    token=oauth.OAuthToken.from_string(credentials.token))
        ret = oauth.fetchResponse(oauthRequest, network.base_url).read()
        friends = utils.fromXML(ret).person
        return [urlparse.parse_qs(y['site_standard_profile_request']['url'])['key'][0] for y in friends if y['site_standard_profile_request']]

        


class SocialPostHandler(BaseHandler):
    allowed_methods = ('POST',)
    
    @login_required
    def create(self, request, response):
        """
        Post a message a social network for a user that has registered us with that network
        API Handler: POST /social/post
        PARAMS
             @network [string] {twitter|facebook} Name of the network to post to
             @message [string] message to be posted
        """
        profile = request.user.get_profile()
        networks = request.POST.get('network')
        
        networks = [n.strip() for n in network.split('|') if n.strip()]
        
        try:
            network = SocialNetwork.objects.get(name=network)
        except SocialNetwork.DoesNotExist:
            return response.send(errors='Invalid network', status=404)
        
        try:
            credentials = UserNetworkCredentials.objects.get(network=network, profile=profile)
        except UserNetworkCredentials.DoesNotExist:
            return response.send(errors="This user has not registered us with the network specified")
        
        
        try:
            #Call the name of the network as a helper method to implement the different posts
            getattr(self, network.name)(request, credentials, network)
        except HTTPError:
            return response.send(errors=NETWORK_HTTP_ERROR % network.name)
        
        return response.send()
    
    def twitter(self, request, credentials, network):
        message = self.get_twitter_post_data(request)
        oauthRequest = oauth.makeOauthRequestObject('https://%s/1/statuses/update.json' % network.base_url, 
                                                    network.getCredentials(), token=oauth.OAuthToken.from_string(credentials.token), 
                                                    method='POST', params={'status': message})
        oauth.fetchResponse(oauthRequest, network.base_url)
        
    def facebook(self, request, credentials, network):
        postData = {'access_token': credentials.token}
        postData.update(self.get_facebook_post_data(request))
        utils.makeAPICall(network.base_url,
                          '%s/feed' % credentials.uuid,
                           postData=postData,
                           secure=True, deserializeAs='skip')   
    
    def linkedin(self, request, credentials, network):
        oauthRequest = oauth.makeOauthRequestObject('https://api.linkedin.com/v1/people/~/person-activities', 
                                                    network.getCredentials(), token=oauth.OAuthToken.from_string(credentials.token), 
                                                    method='POST')
        headers = {'content_type':'application/xml'}
        message = self.get_linkedin_post_data(request)
        raw_body = '<activity locale="en_US"><content-type>linkedin-html</content-type><body>%s</body></activity>' % message
        oauth.fetchResponse(oauthRequest, network.base_url, headers=headers, raw_body=raw_body)

    def get_facebook_post_data(self, request):
        """
        Return a dictionary of parameters you'd like to augment the messge with
        Go here to see what the possible parameters are: you'd like to give to the posted message to facebook
        """
        message = request.POST.get('message')
        if message:
            return {'message': message}
        return {}

    def get_linkedin_post_data(self, request):
        """
        Return the string to post to Linked-in
        """
        message = request.POST.get('message')
        if message:
            return message
        return ''

    def get_twitter_post_data(self, request):
        """
        Return the string to post to Twitter
        """
        message = request.POST.get('message')
        if message:
            return message
        return ''
    
class SocialRegisterHandler(BaseHandler):
    allowed_methods = ('POST', 'GET')
    
    model = SocialNetwork
    
    @login_required
    def read(self, request, network, response=None):
        """
        Handler to allow GETs to this url
        """
        return self.create(request, network, response)
        
    @login_required
    def create(self, request, network, response=None):
        """
        Attempts to gain permission to a user's data with a social network, if successful, will 
        return a redirect to the network's servers, there the user will be prompted to login if 
        necessary, and allow or deny us access. network = {facebook|twitter|linkedin}
        API handler: POST /social/register/{network}
        Params:
            None
        """
        profile = request.user.get_profile()
        if request.META.get('HTTP_REFERER'):
            request.session['last_url'] = request.META['HTTP_REFERER']
        if not response:
            response = ResponseObject()
        
        try:
            network = SocialNetwork.objects.get(name=network)
        except SocialNetwork.DoesNotExist:
            return response.send(errors='Invalid network', status=404)
                
        #return the results of the helper function that has the name of the network referenced
        return getattr(self, network.name)(request, network, response)
        
        
    def facebook(self, request, network, response):
        """
        Helper function to handle facebook redirect
        """        
        args = urllib.urlencode({'client_id' : network.getAppId(),
                                 'redirect_uri': network.getCallBackURL(request),
                                 'scope': network.scope_string,
                                 'display': 'touch'})
    
        return HttpResponseRedirect(network.getAuthURL() + '?' + args)
    
    def twitter(self, request, network, response):
        """
        Helper function to handle twitter redirect
        """
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
    
    def linkedin(self, request, network, response):
        """
        Helper function to handle the linkedin redirect
        """
        return self.twitter(request, network, response)
    
    
class SocialCallbackHandler(BaseHandler):
    allowed_methods = ('GET',)
    
    internal = True
    
    @login_required
    def read(self, request, network, response=None):
        """
        This is the entrypoint for social network's callbacks
        API Handler: GET DONOTUSE
        Params:
            None
        """
        profile = request.user.get_profile()        

        if not response:
            response = ResponseObject()

        try:
            network = SocialNetwork.objects.get(name=network)
        except SocialNetwork.DoesNotExist:
            return response.send(errors='Invalid network', status=404)
        
        #Use the name of the network to call the helper function
        if request.session.get('last_url'):
            getattr(self, network.name)(request, network, profile, response)
            return HttpResponseRedirect(request.session.get('last_url'))
        return getattr(self, network.name)(request, network, profile, response)
        
        
    def twitter(self, request, network, profile, response):
        """
        Helper function to handle the callbacks for twitter 
        """
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
        params = urlparse.parse_qs(accessToken)
        
        if network.name == 'linkedin':
            oauthRequest = oauth.makeOauthRequestObject('https://%s/v1/people/~' % network.base_url,
                                network.getCredentials(), token=oauth.OAuthToken.from_string(accessToken),
                                method='GET')
            ret = oauth.fetchResponse(oauthRequest, network.base_url).read()
            ret = utils.fromXML(ret)
            params['user_id'] = [urlparse.parse_qs(ret['site_standard_profile_request']['url'])['key'][0], '0']
            params['screen_name'] = ['%s %s' % (ret['first_name'], ret['last_name']), '0']
            
        UserNetworkCredentials.objects.filter(profile=profile, network=network).delete()
        UserNetworkCredentials.objects.create(access_token=accessToken,
                                              profile=profile,
                                              network=network,
                                              uuid=params['user_id'][0],
                                              name_in_network=params['screen_name'][0])
        return response.send()


    def facebook(self, request, network, profile, response):
        """
        Helper function to handle the callbacks for facebook
        """
        
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
        
        
        UserNetworkCredentials.objects.filter(profile=profile, network=network).delete()
        UserNetworkCredentials.objects.create(access_token=access_token,
                                              profile=profile,
                                              network=network,
                                              uuid=ret['id'],
                                              name_in_network=ret['name'])
        return response.send()
    
    def linkedin(self, request, network, profile, response):
        """
        Helper function to handle the callbacks for linkedin
        """
        return self.twitter(request, network, profile, response)
