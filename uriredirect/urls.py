from django.conf.urls import  url

from . import views

urlpatterns =  [
    url(r'^(?P<registry_label>.+?)/(?P<requested_uri>.+?)(?P<requested_extension>\.[a-zA-Z]{3,4})?$', views.resolve_uri, name='resolve_uri'),
    url(r'^(?P<registry_label>[^/]+?)(?P<requested_extension>\.[a-zA-Z]{3,4})?$', views.resolve_register_uri, name='resolve_register_uri'),                  
    url(r'^(?P<registry_label>[^/]*?)/(?P<requested_extension>\.[a-zA-Z]{3,4})?$', views.resolve_registerslash_uri, name='resolve_registerslash_uri'),  ]                       
