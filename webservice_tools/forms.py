from django.forms import ModelForm
from copy import deepcopy
class ExtModelForm(ModelForm):
    """
    Extend the model form to allow updating an instance.
    Basically, when passed an instance into the init() method, no fields are required, 
    Also, save a copy of the instance so django doesn't muck it up.
    """
    def __init__(self, *args, **kwargs):
        self.editing = False
        super(ExtModelForm, self).__init__(*args, **kwargs)
        self.temp_instance = deepcopy(self.instance)
        if hasattr(self, 'instance') and  self.instance.pk is not None:
            self.editing = True
            for key in self.fields:
                self.fields[key].required = False
    
    
    def save(self, *args, **kwargs):
        if self.editing:
            for k, v in self.cleaned_data.items():
                if getattr(self.instance, k) and v:
                    setattr(self.temp_instance, k, getattr(self.instance, k))
            self.instance = self.temp_instance
            return super(ExtModelForm, self).save(*args, **kwargs)
        
        else:
            return super(ExtModelForm, self).save(*args, **kwargs)


