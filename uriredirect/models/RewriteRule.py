from django.db import models
from AcceptMapping import AcceptMapping
import mimeparse, re
from django.db.models.loading import get_model


class RewriteRule(models.Model):
    class Meta:
        app_label = 'uriredirect'
        verbose_name = 'Rewrite Rule'
        verbose_name_plural = 'Rewrite Rules'
        
    register = models.ForeignKey(
        'UriRegister',
        help_text='The URI Register to which this rewrite rule belongs'                             
    )
        
    label = models.CharField(
        max_length=100, 
        help_text='A label for this URI, for recognition in the admin interface'
    )
    
    description = models.TextField(
        blank=True, 
        help_text='(Optional) Free-text description of this URI',
    )
    
    pattern = models.CharField(
        max_length=1000, 
        blank=True, 
        help_text='Regular Expression for this URI to capture. See http://docs.python.org/release/2.5.2/lib/re-syntax.html for syntax guidelines.'
    )

    representations = models.ManyToManyField(
        'MediaType', 
        through='AcceptMapping',
    )
      
    def __unicode__(self):
        return self.pattern
    
    def content_negotiation(self, accept):
        available_mime_types = [ media.mime_type for media in self.representations.all() ]
        if len(available_mime_types) == 0: return [], ''
        
        matching_content_type = mimeparse.best_match(available_mime_types, accept)
        accept_mappings = AcceptMapping.objects.filter(
            rewrite_rule = self,
            media_type__mime_type = matching_content_type
        )
        return [ mapping.redirect_to for mapping in accept_mappings ], matching_content_type
    
    def resolve_url_template(self, requested_uri, url_template):
        match = re.match(self.pattern, requested_uri)
        if match.lastindex != None:
            for i in range(match.lastindex):
                url_template = re.sub('\$' + str(i + 1), match.group(i + 1), url_template)
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


