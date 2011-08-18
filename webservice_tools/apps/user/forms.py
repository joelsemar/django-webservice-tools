from django.contrib.auth.models import User
from django import forms
from django.forms import  ValidationError
from django.db.models import Q
from webservice_tools.forms import ExtModelForm
class BaseUserForm(ExtModelForm):
        
    class Meta:
        model = User
        exclude = ('date_joined', 'last_login')
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            if User.objects.filter(~Q(id=self.instance.id), email__iexact=email):
                raise ValidationError('Email already in use')
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            if User.objects.filter(~Q(id=self.instance.id), username__iexact=username):
                raise ValidationError('That username is  already in use')
            
        return username
    
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        self.instance.set_password(password)
        return self.instance.password