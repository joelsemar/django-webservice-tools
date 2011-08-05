from django.forms import ModelForm
from copy import deepcopy
from django.db.models.fields import NOT_PROVIDED



class ExtModelForm(ModelForm):
    """
    This version of ModelForm does a few things:
        1.) set defaults in the incoming data, so that the defaults defined in the model are used 
            (because we don't use the html forms
        2.)Extend the model form to allow updating an instance without providing EVERY single field
           Basically, when passed an instance into the init() method, no fields are required, 
           Also, save a copy of the instance so django doesn't muck it up.
    """
    def __init__(self, *args, **kwargs):
        self.editing = False
        t_args = [a for a in args]
        query_dict = deepcopy(t_args[0])
        opts = self._meta
        for field in opts.model._meta.fields:
            if field.default != NOT_PROVIDED and not query_dict.get(field.name):
                query_dict[field.name] = field.default
        
        t_args[0] = query_dict
        super(ExtModelForm, self).__init__(*tuple(t_args), **kwargs)
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


