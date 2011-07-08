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
        if True:#self.editing:
            instance = self.temp_instance
            for k, v in self.cleaned_data.items():
                if v is not None and self.data.get(k):
                    setattr(instance, k, v)
            instance.save()
            super(ExtModelForm, self).save(*args, **kwargs)
        else:
            import pydevd;pydevd.settrace('127.0.0.1')
            return super(ExtModelForm, self).save(*args, **kwargs)


