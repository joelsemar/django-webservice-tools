import os
import datetime
from django.db.models.signals import post_save
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.utils.importlib import import_module
import sys
from django.db.models.base import ModelBase
from webservice_tools import  utils
from webservice_tools.response_util import message_sent

if not hasattr(settings, 'BADGE_CONSTS'):
    raise Exception("Please provide settings.BADGE_CONSTS to use the badge module.")
consts = import_module(settings.BADGE_CONSTS)

class BadgeModel(models.Model):
    id = models.AutoField(primary_key=True)
    winners = models.ManyToManyField(settings.AUTH_PROFILE_MODULE, related_name="badges", through='BadgeToUser')
    name = models.CharField(max_length=32)
    description = models.CharField(max_length=128, blank=True)
    won_description = models.CharField(max_length=128, blank=True)
    one_time_only = models.BooleanField(default=False)
    badge_action = models.CharField(choices=consts.BADGE_ACTION_CHOICES, max_length=32)
    badge_type = models.CharField(choices=consts.BADGE_TYPE_CHOICES, default='', max_length=32)
    required_number = models.PositiveIntegerField(default=0)
    badge_order = models.PositiveIntegerField(default=0)
    
    @property
    def title(self):
        return self.name.title()
    
    
    def __unicode__(self):
        return u"%s" % self.title
    
    @property
    def images(self):
        images = BadgeImage.objects.filter(badge=self)
        ret = {}
        for image in images:
            ret[image.image_type] = image.image.url
        return ret
    
    
    
    
def badge_upload_to(instance, filename):
    return os.path.join('images/badges', '%s-%s.png' % (datetime.datetime.utcnow().strftime('%M%S%f'),filename.split('.')[0]))

class BadgeImage(models.Model):
    badge = models.ForeignKey(BadgeModel)
    image_type = models.CharField(max_length=128)
    image = models.ImageField(upload_to=badge_upload_to)

    
class BadgeToUser(models.Model):
    id = models.AutoField(primary_key=True)
    badge = models.ForeignKey(BadgeModel)
    winner = models.ForeignKey(settings.AUTH_PROFILE_MODULE)
    when_created = models.DateTimeField(default=datetime.datetime.utcnow)
    
    def save(self, *args, **kwargs):
        if not self.id:
            if hasattr(consts, 'BADGE_AWARDED_TEMPLATE'):
                message_template = consts.BADGE_AWARDED_TEMPLATE
            else:
                message_template =  "You've earned the %(name)s badge!"
            badge = self.badge
            message_text = message_template % {'name': badge.name}
            message_data = utils.toDict(self.badge)
            message_data['images'] = badge.images
            message_data['message'] = message_text
            message_data['type'] = 'badge_event'
            message_sent.send(sender=self.winner.user, message=message_data)
            
        super(BadgeToUser, self).save(*args, **kwargs)


class BadgeMeta(type):
    def __new__(cls, name, bases, attrs):
        new_badge = super(BadgeMeta, cls).__new__(cls, name, bases, attrs)
        parents = [b for b in bases if isinstance(b, BadgeMeta)]
        if not parents:
            # If this isn't a subclass of BadgeMeta, don't do anything special.
            return new_badge
        return register(new_badge)

registered_badges = {}

def register(badge):
    if badge.id not in registered_badges:
        registered_badges[badge.id] = badge()
    return badge

class BaseBadge(object):
    
    __metaclass__ = BadgeMeta
    
    def get_user(self, instance):
        """
        Return the user this action pertains to
        """
        return instance.profile
    
    def callback(self, **kwargs):
        badges = BadgeModel.objects.filter(badge_action=self.action)
        instance = kwargs['instance']
        user = self.get_user(instance)
        for badge in badges:
            if badge.one_time_only:
                    try:
                        BadgeToUser.objects.get(badge=badge, winner=user)
                        continue
                    except BadgeToUser.DoesNotExist:
                        pass
            if self.check_badge(user, badge, instance):
                BadgeToUser.objects.create(badge=badge, winner=user)
                self.badge_won_callback(user, badge, instance)

    def badge_won_callback(self, user, badge, instance):
        pass
    
    def __init__(self):
        post_save.connect(self.callback, sender=self.model) 


BADGES_EARNED = 'be'
class BadgesEarnedBadge(BaseBadge):
    """
    This is an example badge (Though it does work)
    You define a class that
     
      a.) Inherits from 'BaseBadge'
      b.) has an 'action' with a corresponding BadgeModel row (pulled from your BADGE_CONSTS file)
      c.) defines a get_user() method for awarding the badge
         (must return an instance of the class defined in settings.AUTH_PROFILE_MODULE)
      d.) defines a check_badge() method for the badge logic (returns a Boolean)
      
    This badge awards a user a badge for earning badges :)
    """
    action = BADGES_EARNED
    model = BadgeToUser
    id = "BadgesEarned"
    def get_user(self, instance):
        return instance.winner
    
    def check_badge(self, user, badge):
        return BadgeToUser.objects.filter(winner=user).count() >= badge.required_number

#ALL DEFINITION EOF
module_name = globals().get('__name__')
models = sys.modules[module_name]
models._all_ = []
for model_name in dir():
    m = getattr(models, model_name)
    if isinstance(m, ModelBase) and not m._meta.abstract:
        models._all_.append(model_name)