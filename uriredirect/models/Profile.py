from django.db import models

class ProfileManager(models.Manager):
    def get_by_natural_key(self, token):
        return self.get(token=token)

class Profile(models.Model):
    """ a Profile is a named view for an alternative representation of a resource. 
    
    Definitions support "content negotiation by profile" according to https://www.w3.org/TR/dx-prof-conneg/ 
    
    Profiles may be defined in a non-cyclic specialisation graph (a single profile may be a profile of one or more other profiles, and be returned as a valid response if the more general profile is requested.
    """
    readonly_fields = ('profilesTransitive',)
    profilesTransitive = ()
    
    class Meta:
        app_label = 'uriredirect'
        ordering = ['token']
        verbose_name = 'Profile (View)'
        verbose_name_plural = 'Profiles (Views)'

    
    objects = ProfileManager()
    
    def natural_key(self):
        return(self.token,)
        
    token = models.CharField(
        max_length=100, blank=False, null=False,
        unique = True, help_text='A comma separated list of short tokens this profile may be invoked by'
    )
    
    mediaprofs = models.CharField(
        max_length=1000, blank=True, null = True, 
        unique = True, help_text='a comma separated list of media-types with profiles such as "application/gml+xml; version=3.2" that match this profile. This is an extension point not yet used.'  
    )
    
    uri = models.URLField(
        max_length=1000, 
        blank=False, null=False, verbose_name = 'Canonical URI',
        help_text = 'The canonical URI of the profile - this is what an external system needs to check to determine what a token means'
    )
    
    label = models.CharField(
        max_length=100, 
        blank=True, null=True, verbose_name = 'Display Label',
        help_text = 'Display label for profile'
    )
    
    comment = models.TextField(
        max_length=1000, 
        blank=True, null=True, verbose_name = 'Description',
        help_text = 'The canonical URI of the profile - this is what an external system needs to check to determine what a token means'
    )
    
    profiles = models.ManyToManyField( "Profile", blank=True,
       help_text= 'Profiles may be defined in a non-cyclic specialisation graph (a single profile may be a profile of one or more other profiles, and be returned as a valid response if the more general profile is requested.'
    )
    
    profilesTransitive = models.ManyToManyField( "Profile", blank=True, related_name='ancestors',
       help_text= 'Calculated list of all profiles that are ancestors of this one'
    )
    
    def getTokenURI(self):
        """ Get a tuple of token and URI 
        """
        return ( self.token, self.uri) 
        
    def __unicode__(self):
        return self.token
        


      

        
        