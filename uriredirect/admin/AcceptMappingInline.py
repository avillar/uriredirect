from django.contrib import admin
from uriredirect.models import AcceptMapping
from django import forms

class AcceptMappingInlineForm(forms.ModelForm):
    rewrite_rule = forms.CharField(widget=forms.TextInput(attrs={'size':200}))
    
class AcceptMappingInline(admin.TabularInline):
    model = AcceptMapping
    form = AcceptMappingInlineForm
    extra = 2