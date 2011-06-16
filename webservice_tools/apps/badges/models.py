import os
import datetime
from django.db.models.signals import post_save
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.utils.importlib import import_module

from webservice_tools import  utils
from webservice_tools.response_util import message_sent

if not hasattr(settings, 'BADGE_CONSTS'):
    raise Exception("Please provide settings.BADGE_CONSTS to use the badge module.")
consts = import_module(settings.BADGE_CONSTS)

def thumb_path(instance, filename):
    return os.path.join('images/thumbs', '%s.png' % instance.name)

def image_path(instance, filename):
    return os.path.join('images/full', '%s.png' % instance.name)

def hi_res_thumb_path(instance, filename):
    return os.path.join('images/hi-res-thumb', '%s@2x.png' % instance.name)

def hi_res_image_path(instance, filename):
    return os.path.join('images/hi-res-full', '%s@2x.png' % instance.name)


class BadgeModel(models.Model):
    id = models.AutoField(primary_key=True)
    winners = models.ManyToManyField(settings.AUTH_PROFILE_MODULE, related_name="badges", through='BadgeToUser')
    name = models.CharField(max_length=32)
    description = models.CharField(max_length=128, blank=True)
    won_description = models.CharField(max_length=128, blank=True)
    one_time_only = models.BooleanField(default=False)
    thumb = models.ImageField(upload_to=thumb_path, blank=True, null=True)
    image = models.ImageField(upload_to=image_path, blank=True, null=True)
    hi_res_thumb = models.ImageField(upload_to=hi_res_thumb_path, blank=True, null=True)
    hi_res_image = models.ImageField(upload_to=hi_res_image_path, blank=True, null=True)
    badge_action = models.CharField(choices=consts.BADGE_ACTION_CHOICES, max_length=32)
    badge_type = models.CharField(choices=consts.BADGE_TYPE_CHOICES, default='')
    required_number = models.PositiveIntegerField(default=0)
    badge_order = models.PositiveIntegerField(default=0)
    
    @property
    def title(self):
        return self.name.title()
    
    
    def __unicode__(self):
        return u"%s" % self.title

    
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
            message_text = message_template % {'name': self.badge.name}
            message_data = utils.toDict(self.badge)
            message_sent.send(sender=self.winner.user, message=[message_text, message_data])
            badge = self.badge
            if badge.badge_type == consts.RANK_BADGE:
                self.winner.rank_badge = badge.thumb and badge.thumb.url or ''
                self.winner.hi_res_rank_badge = badge.hi_res_thumb and badge.hi_res_thumb.url or ''
                self.winner.save()
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

