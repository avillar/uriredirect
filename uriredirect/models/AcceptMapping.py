from django.db import models


class AcceptMappingManager(models.Manager):
    def get_by_natural_key(self, rewrite_rule,media_type):
        return self.get(rewrite_rule=rewrite_rule,media_type=media_type)
        
class AcceptMapping(models.Model):
    class Meta:
        app_label = 'uriredirect'
        verbose_name = 'Accept-Mapping'
        verbose_name_plural = 'Accept-Mapping'
    
    objects = AcceptMappingManager()
        
    def natural_key(self):
        return(self.rewrite_rule, self.media_type)
        
    rewrite_rule = models.ForeignKey('RewriteRule',on_delete=models.CASCADE)
    profile = models.ForeignKey('Profile',null=True, on_delete=models.SET_NULL , help_text='The profile to report if used as a default' )
    media_type = models.ForeignKey(
        'MediaType',
        verbose_name = 'Media Type' , on_delete=models.CASCADE
    )
    redirect_to = models.CharField(
        max_length=2000,
        help_text='The URL or URL template to which the specified Representation Type should redirect. Templates may use positional variables ($1,$2) from the rule pattern, additional parameters ${param} or ${param=default} if a default value is to be used, or query params $q{queryparam}. URLencoding is enforced using ! before the variable name ${!var}'
    )
    
    def __unicode__(self):
        return self.media_type.mime_type
        
                
    def __str__(self):
        return str(self.media_type.mime_type)