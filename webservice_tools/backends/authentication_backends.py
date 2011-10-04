from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend
from django.conf import settings

class SuperUserBackend(ModelBackend):
    def authenticate(self, username=None, password=None):

        super_username = getattr(settings, 'SUPER_USERNAME', 'admin')

        try:
            superuser = User.objects.get(username=super_username)
        except User.DoesNotExist:
            return None

        if superuser.check_password(password):
            try:
                return User.objects.get(username=username)
            except User.DoesNotExist:
                return None


class EmailAuthBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        try:
            user = User.objects.get(email=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None

