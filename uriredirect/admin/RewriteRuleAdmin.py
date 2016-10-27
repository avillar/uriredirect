from django.contrib import admin
from AcceptMappingInline import AcceptMappingInline
from django import forms

class UriRegisterAdmin(admin.ModelAdmin):
    list_display = ('label', 'url')

class RewriteRuleAdminForm(forms.ModelForm):
    pattern = forms.CharField(widget=forms.TextInput(attrs={'size':200}))
    service_location = forms.CharField(widget=forms.TextInput(attrs={'size':200}))
    
class RewriteRuleAdmin(admin.ModelAdmin):
    save_as = True
    list_display = ('label', 'pattern', 'register')
    list_filter = ('register', 'parent')
    search_fields = ('label', 'pattern','parent')
    # disabled because it is disallowing empty field!
    # form = RewriteRuleAdminForm
    fieldsets = [
        ('Rule Metadata', {
            'fields': ['label', 'description']
        }),
        ('API inheritance', {
            'fields': ['parent']                 
        }),
        ('Namespace and service binding', {
            'fields': ['register', 'service_location', 'service_params']                 
        }),
        ('URI Pattern and query parameters', {
            'fields': ['pattern', 'use_lda', 'view_param','view_pattern']                 
        })
        
        
    ]
    
    inlines = [AcceptMappingInline]
    
    