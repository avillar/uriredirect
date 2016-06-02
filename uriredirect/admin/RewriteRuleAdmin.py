from django.contrib import admin
from AcceptMappingInline import AcceptMappingInline

class RewriteRuleAdmin(admin.ModelAdmin):
    list_display = ('label', 'pattern', 'register')
    list_filter = ('register',)
    search_fields = ('label', 'pattern','parent')
    
    fieldsets = [
        ('Rule Metadata', {
            'fields': ['label', 'description']
        }),
        ('API inheritance', {
            'fields': ['parent']                 
        }),
        ('Namespare and service binding', {
            'fields': ['register', 'service_location', 'service_params']                 
        }),
        ('URI Pattern and query parameters', {
            'fields': ['pattern', 'use_lda', 'view_param','view_pattern']                 
        })
        
        
    ]
    
    inlines = [AcceptMappingInline]
    
    