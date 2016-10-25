from django.contrib import admin
from RewriteRuleAdmin import RewriteRuleAdmin, UriRegisterAdmin
from uriredirect.models import RewriteRule, MediaType, UriRegister

admin.site.register(RewriteRule, RewriteRuleAdmin)
admin.site.register(MediaType)
admin.site.register(UriRegister, UriRegisterAdmin)