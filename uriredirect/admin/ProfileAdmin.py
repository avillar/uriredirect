from django.contrib import admin
from .AcceptMappingInline import AcceptMappingInline
from django import forms
#from uriredirect.models import *
from django.db.models import Q

class ProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.fields['profiles'].queryset = Profile.objects.exclude(token=self.instance.token).exclude(profilesTransitive__token=self.instance.token)
        
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('token', 'label','uri')
    form=ProfileForm

    def save_related(self,  request, form, formsets, change):
       #import pdb; pdb.set_trace()
       super(ProfileAdmin, self).save_related( request, form, formsets, change) 
       form.instance.profilesTransitive.remove(*form.instance.profilesTransitive.all())
       for p in form.instance.profiles.all():
         self.add_recursive(form.instance,form.instance.profilesTransitive,p)
         
    def add_recursive(self,instance,qset,profile):
        if profile.id == instance.id :
            raise Exception("Profile inheritance loop detected")
        elif not qset.filter(id=profile.id).exists():
            qset.add(profile)
            for rp in profile.profiles.all():
                self.add_recursive(instance,qset,rp)
        
                