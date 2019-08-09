from django.db import models
from RewriteRule import RewriteRule
import re


class UriRegisterManager(models.Manager):
    def get_by_natural_key(self, label):
        return self.get(label=label)
        
class UriRegister(models.Model):
    class Meta:
        app_label = 'uriredirect'
        verbose_name = 'URI Registry'
        verbose_name_plural = 'URI Registries'
    objects = UriRegisterManager()

    def natural_key(self):
        return(self.label,)
        
    label = models.CharField(
        max_length=50,
        unique=True,
        help_text='A label that uniquely identifies a particular URI register'                                  
    )
    
    url = models.URLField( blank=True, null=True,
        help_text='The absolute URL of a server at which this URI register can be reached. May be left blank, in which case the incoming request will be used.'                      
    )
    
    can_be_resolved = models.BooleanField(
        help_text='Determines whether this server will resolve URIs for this URI register (false will forward to the Uri for remote resolution)'                                     
    )
    
    def __unicode__(self):
        return self.label
    
    def find_matching_rules(self, requested_uri):
        """
            returns a list of rules that are bound to this URI register. - these may inherited, and have inheriting sub-rules that will need ot be accessed
        """
        rulesfound = []
        for rule in RewriteRule.objects.filter(register=self) :
            (matched,nestedrule) = rule.match_inheritance( requested_uri)
            if matched :
                rulechain = (rule,) + nestedrule.get_subrules() + (nestedrule,)
                rulesfound.append(rulechain)
                # get all sub rules not bound to a register 
        return rulesfound


        
    def construct_remote_uri(self, requested_uri):
        return "/".join([self.url.rstrip('/'), requested_uri.lstrip('/')])