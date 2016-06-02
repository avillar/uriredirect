from django.db import models

class MediaTypeManager(models.Manager):
    def get_by_natural_key(self, mime_type):
        return self.get(mime_type=mime_type)

class MediaType(models.Model):
    class Meta:
        app_label = 'uriredirect'
        ordering = ['file_extension']
        verbose_name = 'Media Type'
        verbose_name_plural = 'Media Types'
    
    objects = MediaTypeManager()
    
    def natural_key(self):
        return(self.mime_type)
        
    mime_type = models.CharField(
        max_length=100,
        unique = True
    )
    
    file_extension = models.CharField(
        max_length=100,
    )
        
    def __unicode__(self):
        return self.mime_type