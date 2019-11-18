from django import template

register = template.Library()

@register.filter
def getdictval(dict, key):    
    try:
        return dict[key]
    except KeyError:
        return ''