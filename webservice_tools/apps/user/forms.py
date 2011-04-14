from django.contrib.auth.models import User
from django import forms
from django.forms import  ValidationError
from webservice_tools.forms import ExtModelForm
class BaseUserForm(ExtModelForm):
        
    class Meta:
        model = User
        exclude = ('date_joined', 'last_login')
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            try:
                User.objects.get(email=email)
                raise ValidationError('Email already in use')
            except User.DoesNotExist:
                pass
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            try:
                User.objects.get(username=username)
                raise ValidationError('That username is  already in use')
            except User.DoesNotExist:
                pass
            
        return username
    
