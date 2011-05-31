from piston.handler import BaseHandler
from webservice_tools.decorators import login_required
from webservice_tools.response_util import ResponseObject
from django.db import models
from webservice_tools.apps.badges.models import BadgeToUser, BadgeModel, consts
from django.conf import settings
app_label, model_name = settings.AUTH_PROFILE_MODULE.split('.')
PROFILE_MODEL = models.get_model(app_label, model_name)

class BadgeHandler(BaseHandler):
    allowed_methods = ('GET',)
    
    @login_required
    def read(self, request, id, response):
        """
        Return a list of all badges and whether or not this user has won them
        API Handler: GET /badges/{id}
        """
        all_badges = BadgeModel.objects.all()
        profile = PROFILE_MODEL.objects.get(id=id)
        users_badges = [b.badge for b in BadgeToUser.objects.filter(winner=profile)]
        
        ret = []
        for badge in all_badges:
                ret.append({'name': badge.name,
                            'description': badge.description,
                            'won_description': badge.won_description,
                            'thumb_url': badge.thumb and badge.thumb.url or '',
                            'image_url': badge.image and badge.image.url or '',
                            'hi_res_thumb_url': badge.hi_res_thumb and badge.hi_res_thumb.url or '',
                            'hi_res_image_url': badge.hi_res_image and badge.hi_res_image.url or '',
                            'order': badge.badge_order,
                            'won': badge in users_badges})
                
        response.set(badges=ret)
        return response.send()
