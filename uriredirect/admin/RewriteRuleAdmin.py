from django.contrib import admin
from .AcceptMappingInline import AcceptMappingInline
from django import forms
from uriredirect.models import *
from django.db.models import Q

class UriRegisterAdmin(admin.ModelAdmin):
    list_display = ('label', 'url')

class RewriteRuleAdminForm(forms.ModelForm):
    pattern = forms.CharField(widget=forms.TextInput(attrs={'size':200}))
    service_location = forms.CharField(widget=forms.TextInput(attrs={'size':200}))

class AcceptMappingAdmin(admin.ModelAdmin):
    list_display = ( 'media_type', 'rewrite_rule', 'redirect_to')
    search_fields = ( 'media_type__mime_type', 'redirect_to' )
    list_filter = ('rewrite_rule',)

class APIUsedFilter(admin.SimpleListFilter):
    title='API (Register bound)'
    parameter_name = 'api_id'
    
    def lookups(self, request, model_admin):
        rules = RewriteRule.objects.filter(register__isnull=True, parent__isnull=True)        
        return set([(c.id, c.label) for c in rules])
        
    def queryset(self, request, qs):
        try:
            qs= qs.filter(parent__id=request.GET['api_id'], register__isnull=False)
        except:
            pass
        return qs

class APIPartFilter(admin.SimpleListFilter):
    title='RewriteRule (API)'
    parameter_name = 'apiroot_id'
    
    def lookups(self, request, model_admin):
        rules = RewriteRule.objects.filter(register__isnull=True, parent__isnull=True)        
        return [(c.id, c.label) for c in rules]
        
    def queryset(self, request, qs):
        try:
            api_id = request.GET['apiroot_id'] 
            qs= qs.filter(Q(parent__id=api_id) | Q(parent__parent__id=api_id), register__isnull=True)
        except Exception as e:
            print (e)
            pass
        return qs
        
class RegisterFilter(admin.SimpleListFilter):
    title='Register (API bindings)'
    parameter_name = 'reg_id'
    
    def lookups(self, request, model_admin):
        rules = RewriteRule.objects.filter(register__isnull=False, parent__isnull=False)        
        return set([(c.register.id, c.register.label) for c in rules])
        
    def queryset(self, request, qs):
        try:
            qs= qs.filter(register__id=request.GET['reg_id'])
        except:
            pass
        return qs 

class ProfileFilter(admin.SimpleListFilter):
    title='Data Profile'
    parameter_name = 'profile'
    
    def lookups(self, request, model_admin):
        profiles = Profile.objects.all()        
        return set([(c.id, c.token) for c in profiles])
        
    def queryset(self, request, qs):
        try:
            qs= qs.filter(profile__id=request.GET['profile'])
        except:
            pass
        return qs 
        
class ServerFilter(admin.SimpleListFilter):
    title='Service'
    parameter_name = 'server_uri'
    
    def lookups(self, request, model_admin):
        rules = RewriteRule.objects.filter(service_location__isnull=False)        
        return set([(c.service_location, c.service_location) for c in rules])
        
    def queryset(self, request, qs):
        try:
            qs= qs.filter(service_location=request.GET['server_uri'])
        except:
            pass
        return qs 
        
class RegisterRuleFilter(admin.SimpleListFilter):
    title='Register (custom rules)'
    parameter_name = 'regrule_id'
    
    def lookups(self, request, model_admin):
        rules = RewriteRule.objects.filter(register__isnull=False, parent__isnull=True)        
        return set([(c.register.id, c.register.label) for c in rules])
        
    def queryset(self, request, qs):
        try:
            qs= qs.filter(register__id=request.GET['regrule_id'])
        except:
            pass
        return qs 

    
class RegisterAPIBinding(RewriteRule):
    class Meta:
        proxy = True
        verbose_name = 'RewriteRule: Register/API binding'


        
class RegisterAPIBindingAdmin(admin.ModelAdmin):
    """ Subset of rewrite rules binding APIs to registers """
    save_as = True
    model=RegisterAPIBinding
    list_display = ('label',  'register', 'parent',)
    list_filter = (APIUsedFilter,)
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
        })
        
        
    ]
    
    def get_queryset(self, request):
        qs = super(RegisterAPIBindingAdmin, self).get_queryset(request)
        return qs.filter(register__isnull=False,parent__isnull=False)
 
class APIRootRule(RewriteRule):
    class Meta:
        proxy = True
        verbose_name = 'RewriteRule: API base'

class APISubRule(RewriteRule):
        
    class Meta:
        proxy = True
        verbose_name = 'RewriteRule: API subrule'

 
class SubRulesInline(admin.TabularInline):
    model = APISubRule
    fields = ('label','profile')
    extra = 0
    show_change_link = True

class RulePatternsAdminForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super(RulePatternsAdminForm, self).clean()

        if not (bool(self.cleaned_data['view_pattern']) !=
                bool(self.cleaned_data['profile'])):
            raise forms.ValidationError( 'Do not define both a profile and string matching pattern - the profile token will be used.')

        return cleaned_data
        
 
class APIRootRuleAdmin(admin.ModelAdmin):
    form=RulePatternsAdminForm
    save_as = True
    model=APIRootRule
    list_display = ('label', 'pattern', 'register')
    #list_filter = (APIUsedFilter,)
    search_fields = ('label', 'pattern','parent')
    # disabled because it is disallowing empty field!
    # form = RewriteRuleAdminForm
    fieldsets = [
        ('Rule Metadata', {
            'fields': ['label', 'description']
        }),
        ('Namespace and service binding', {
            'fields': ['register', 'service_location', 'service_params']                 
        }),
        ('URI Pattern and query parameters', {
            'fields': ['pattern', 'use_lda', 'profile', 'view_param','view_pattern']                 
        })
        
    ]
    inlines = [AcceptMappingInline, SubRulesInline]
    def get_queryset(self, request):
        #import pdb; pdb.set_trace()
        qs = super(APIRootRuleAdmin, self).get_queryset(request)
        return qs.filter(parent__isnull=True,register__isnull=True) 
 
   
class APISubRuleAdmin(admin.ModelAdmin):
    form=RulePatternsAdminForm
    save_as = True
    model=APISubRule
    list_display = ('label', 'parent','profile_list', 'view_pattern')
    list_filter = (APIPartFilter,)
    search_fields = ('label', 'pattern', )
    # disabled because it is disallowing empty field!
    # form = RewriteRuleAdminForm
    fieldsets = [
        ('Rule Metadata', {
            'fields': ['label', 'description']
        }),
        ('API inheritance', {
            'fields': ['parent']                 
        }),
        ('URI Pattern and query parameters', {
            'fields': ['pattern', 'use_lda', 'profile', 'view_param','view_pattern']                 
        })
        
    ]
    inlines = [AcceptMappingInline]
        
    def get_queryset(self, request):
        qs = super(APISubRuleAdmin, self).get_queryset(request)
        return qs.filter(parent__isnull=False,register__isnull=True) 
        
class RewriteRuleAdmin(admin.ModelAdmin):
    form=RulePatternsAdminForm
    save_as = True
    list_display = ('label', 'pattern', 'register')
    list_filter = (ProfileFilter,RegisterFilter, ServerFilter, RegisterRuleFilter, APIUsedFilter, APIPartFilter)
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
            'fields': ['pattern', 'use_lda', 'profile', 'view_param','view_pattern']                 
        })
        
        
    ]
    
    inlines = [AcceptMappingInline]
   
    def get_queryset_notused(self, request):
        qs = super(RewriteRuleAdmin, self).get_queryset(request)
        return qs.filter(parent__isnull=True,register__isnull=False)
    