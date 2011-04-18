from piston.handler import BaseHandler
from webservice_tools.decorators import login_required
from webservice_tools.response_util import ResponseObject

from webservice_tools.apps.badges.models import BadgeToUser, BadgeModel, consts

class BadgeHandler(BaseHandler):
    allowed_methods = ('GET',)
    
    @login_required
    def read(self, request, response):
        """
        Return a list of all badges and whether or not this user has won them
        API Handler: GET /badges
        """
        all_badges = BadgeModel.objects.all()
        profile = request.user.get_profile()
        users_badges = [b.badge for b in BadgeToUser.objects.filter(winner=profile)]
        
        ret = {}
        for type in consts.BADGE_TYPE_CHOICES:
            ret[type[1]] = []
            for badge in all_badges.filter(badge_type=type[0]):
                ret[type[1]].append({'name': badge.name,
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
