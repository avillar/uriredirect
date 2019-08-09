from django.contrib import admin
from RewriteRuleAdmin import RewriteRuleAdmin, UriRegisterAdmin
from ProfileAdmin import ProfileAdmin
from uriredirect.models import RewriteRule, MediaType, UriRegister, Profile

admin.site.register(RewriteRule, RewriteRuleAdmin)
admin.site.register(MediaType)
admin.site.register(UriRegister, UriRegisterAdmin)
admin.site.register(Profile,ProfileAdmin)