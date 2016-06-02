from django.db import models
from AcceptMapping import AcceptMapping
import mimeparse, re
from django.db.models.loading import get_model

class RewriteRuleManager(models.Manager):
    def get_by_natural_key(self, label):
        return self.get(label=label)

class RewriteRule(models.Model):
    class Meta:
        app_label = 'uriredirect'
        verbose_name = 'Rewrite Rule'
        verbose_name_plural = 'Rewrite Rules'
    
    objects = RewriteRuleManager()

    def natural_key(self):
        return(self.label)
    
        
    label = models.CharField(
        max_length=100,
        unique = True,
        help_text='A label for this URI, for recognition in the admin interface'
    )
    
    register = models.ForeignKey(
        'UriRegister',
        null = True,
        blank = True,
        help_text='The URI register this rule is applied to. If the rule is a reusable API definition leave this unset'                             
    )
    
    parent = models.ForeignKey(
        'RewriteRule',
        help_text='The parent this rule extends - typically a API definition',
        blank = True,
        null = True
    )    
    
    service_location = models.URLField(
        max_length=300,
        null = True,
        blank = True,
        help_text='The base URL of the service this rule is being applied to - if blank all accept-mappings must be absolute URLs'
    )
    
    service_params = models.CharField(
        max_length=500,
        null = True,
        blank = True,
        help_text='a comma separated list of param/value pairs matching ${variable} strings in redirection templates'
    )
    
    description = models.TextField(
        blank=True, 
        help_text='(Optional) Free-text description of this URI',
    )
    
    pattern = models.CharField(
        max_length=1000, 
        blank=True, 
        null = True,
        help_text='Regular Expression for this URI to capture. See http://docs.python.org/release/2.5.2/lib/re-syntax.html for syntax guidelines. If you wish for the rule to match based on a requested file extension, please do not end the pattern with a "$" without including logic to explicitly identify a file extension. If a parent rule is specified, only use this to restrict to s subset of matching patterns'
    )

    use_lda = models.BooleanField(
        default=True,
        verbose_name='Use LDA standard params',
        help_text='Use LDA parameters (_format,_lang) to control content negotiation'
    )
    
    view_param = models.CharField(
        max_length=200, 
        default='_view',
        help_text='Query parameters to match, comma or ;  separated(e.g. LDA _view  defining information model requested )'
    )
    
    view_pattern = models.CharField(
        max_length=500, 
        blank = True,
        null = True,
        help_text='regex patterns for params, separated by semicolons ; '
    )
 
    representations = models.ManyToManyField(
        'MediaType', 
        through='AcceptMapping',
    )
      
    def __unicode__(self):
        return ":".join(filter(None, (self.pattern, self.service_location )))
    
    def extension_match(self, requested_extension):        
        accept_mappings = AcceptMapping.objects.filter(
            rewrite_rule = self,
            media_type__file_extension = requested_extension  
        )
        
        if len(accept_mappings) == 0:
            return [], ''
        else:
            return [ mapping.redirect_to for mapping in accept_mappings ], requested_extension
    
    def get_pattern(self) :
        if self.pattern :
            return self.pattern
        if self.parent :
            return self.parent.get_pattern()
    
    def get_subrules(self) :
        ruleset = ()
        for subrule in RewriteRule.objects.filter(parent=self, register=None) :
            ruleset = ruleset + (subrule, ) + subrule.get_subrules()
        return ruleset

    def match_inheritance ( self, requested_uri ) :
        """
            returns a T/F, and the actual rule from the inheritance tree that matched a pattern
            - the key use case is that an API can be set up against a pattern, and then inherited by a binding to a register (URI base) and service endpoint
        """
        if self.pattern :
            if re.match(self.pattern, requested_uri) != None :
                return (True, self)
        if self.parent :
            return self.parent.match_inheritance ( requested_uri ) 
        return (False, None)
    
    def get_prop_from_tree ( self, propname ) :
        """
            get the first set value of a property walking the rule inheritance tree, and the rule it came from (val,rule()  If a boolean, get first True value
        """
        prop = getattr(self, propname)
        if prop :
            if type(prop) == bool :
                return (prop or (self.parent and self.get_prop_from_tree ( self.parent, propname ) ) , self)
            else :
                return (prop, self)
        if self.parent :
            return self.parent.get_prop_from_tree (  propname ) 
        return (None,None)
        
    def get_param_matches(self):
        """
            walk the inheritance tree collecting all query parameter matches - this is a list of param/value and the associatied rule
        """
        params = []
        return params
        
    def content_negotiation(self, accept):
        available_mime_types = [ media.mime_type for media in self.representations.all() ]
        if len(available_mime_types) == 0: return [], ''
        
        matching_content_type = mimeparse.best_match(available_mime_types, accept)
        accept_mappings = AcceptMapping.objects.filter(
            rewrite_rule = self,
            media_type__mime_type = matching_content_type
        )
        return [ mapping.redirect_to for mapping in accept_mappings ], matching_content_type
    
    
    def get_url_template(self, requested_extension , accept ) :
        # If given a file extension, that should be checked first
        if requested_extension != None:
            url_templates, file_extension = self.extension_match(requested_extension)
            if url_templates :
                return url_templates[0]
            elif self.parent :
                return self.parent.get_url_template( requested_extension , accept )
        
        if accept:
            url_templates, content_type = self.content_negotiation(accept)
            if url_templates :
                return url_templates[0]
            elif self.parent :
                return self.parent.get_url_template( None , accept )
            
        return None    
                
    def resolve_url_template(self, requested_uri, url_template, vars, qvars):
        # get substitution groups from original pattern
        match = re.match(self.get_pattern(), requested_uri)
        if match.lastindex != None:
            for i in range(match.lastindex):
                url_template = re.sub('\$' + str(i + 1), match.group(i + 1), url_template)
                
        # environment variable matching
        varmatch = re.findall(u'\${(\w+)}', url_template)
        for var in varmatch :
            if not vars.get(var) :
                raise ValueError("variable %s not found" % var )
            url_template = re.sub('\${' + var + '}', vars[var], url_template)
            
        # query variable matching
        varmatch = re.findall(u'\$q{(\w+)}', url_template)
        for var in varmatch :
            if not qvars.get(var) :
                raise ValueError("variable %s not found" % var) 
            url_template = re.sub('\${' + var + '}', qvars[var], url_template)  
            
        # Django model pattern matching
        model_match = re.match(u'.*@(\w+:\w+\.\w+:\w+)@.*', url_template)
        if(model_match):
            try:
                django_pattern = model_match.group(1)
                lookup_field = django_pattern.split(':')[0]  # field name we'll use to select the django object
                lookup_model = django_pattern.split(':')[1]  # app_label.model_name
                redirect_field = django_pattern.split(':')[2]  # the field displayed in the new redirect URL
                app_label = lookup_model.split('.')[0]
                model_label = lookup_model.split('.')[1]
                model = get_model(app_label, model_label)
                obj = model.objects.get(**{lookup_field: match.groupdict()[lookup_field]})
                url_template = re.sub(u'@' + django_pattern + u'@', getattr(obj, redirect_field), url_template)
            except model.DoesNotExist:
                return None
        return url_template


