from django.http import HttpResponseNotFound, HttpResponseServerError, HttpResponsePermanentRedirect, HttpResponseNotAllowed
from uriredirect.models import UriRegister
from uriredirect.http import HttpResponseNotAcceptable, HttpResponseSeeOther
import re

def resolve_register_uri(request, registry_label,requested_extension):
    """
        resolve a request to the register itself - just another URI
    """
    return resolve_uri(request, registry_label, None, requested_extension )
    
def resolve_registerslash_uri(request, registry_label,requested_extension):
    """
        resolve a request to the register itself - with a trailing slash
    """
    return resolve_uri(request, registry_label, "/", requested_extension )
    
def resolve_uri(request, registry_label, requested_uri, requested_extension):
    if request.META['REQUEST_METHOD'] != 'GET':
        return HttpResponseNotAllowed(['GET'])
    if requested_extension :
        requested_extension = requested_extension.replace('.','')
    
    try:
        if request.GET['pdb'] :
            import pdb; pdb.set_trace()
    except: pass
    # Determine if this server is aware of the requested registry
    requested_register=None
    default_register=None
    try:
        requested_register = UriRegister.objects.get(label=registry_label)
    except UriRegister.DoesNotExist:
        if requested_uri in [ "/", None ] :
            requested_uri = "".join( filter(None,(registry_label,requested_uri if requested_uri else '')))
        else:
            requested_uri = "/".join( filter(None,(registry_label,requested_uri)))
        
    try:
        default_register = UriRegister.objects.get(label='*')
 
    except UriRegister.DoesNotExist:   
        if not requested_register:
            return HttpResponseNotFound('The requested URI registry does not exist')
    
    # Determine if this server can resolve a URI for the requested registry
    if requested_register and not requested_register.can_be_resolved:
        return HttpResponsePermanentRedirect(requested_register.construct_remote_uri(requested_uri))
    
    # Find rewrite rules matching the requested uri Base - including the rule that binds the rules to a service - so bundled into 
    # rulechains - where first rule is the one bound to the register and service location.
    if requested_register:
        rulechains = requested_register.find_matching_rules(requested_uri)
    if not requested_register or len(rulechains) == 0:
        rulechains = default_register.find_matching_rules(requested_uri)
        requested_register= default_register
        if len(rulechains) == 0:
            return HttpResponseNotFound('The requested URI base does not match base URI pattern for any rewrite rules')
 
    # find subset matching viewname, and other query param constraints

    rule = None # havent found anything yet until we check params

    clientaccept = request.META.get('HTTP_ACCEPT', '*')
    # note will ignore accept header and allow override format/lang in conneg if LDA convention in use
       
    for rulechain in rulechains :
        binding = rulechain[0] 
        for patrule in rulechain :
            (use_lda, ignore) = patrule.get_prop_from_tree('use_lda')
            if use_lda :
                try:
                    requested_extension= request.GET['_format']
                except : pass
                if requested_extension :
                    accept = None
                else :
                    accept = clientaccept # allow content negotiation only if not specified
            else :
                accept = clientaccept
            (queryparams, prule) = patrule.get_prop_from_tree('view_pattern')
            if queryparams :
                viewprops = getattr(prule,'view_param')
                if not viewprops :
                    HttpResponseServerError('view match set but the query parameter to match is not set for rule %s' % patrule)
                try:
                    viewpats = queryparams.split(';')
                    allfound = True
                    for viewprop in viewprops.split(';') :
                        if not re.match(viewpats.pop(0),request.GET[viewprop]):
                            allfound = False
                            break
                    if allfound :
                        # get the URL template for the content type match - starting from the most specialised rule (binding)
                        url_template = patrule.get_url_template(requested_extension, accept)
                        if url_template :
                            rule = patrule 
                except :
                    continue # viewprop not set in request so dont match but keep looking
            elif not rule :  # if no specific query set, then set - otherwise respect any match made by the more specific rule
                url_template = binding.get_url_template(requested_extension, accept)
                if url_template :
                    rule = patrule
        if rule :
            break
                
    if not rule :
        return HttpResponseNotFound('The requested URI base matched but no match for specific query parameters and/or format')
 
    print url_template 
    
    # set up all default variables
    if  requested_uri :
        try:
            term = requested_uri[requested_uri.rindex("/")+1:]
            vars = { 'uri' : "/".join((requested_register.url,requested_uri)) , 'server' : binding.service_location , 'path' : requested_uri, 'term' : term , 'path_base' : requested_uri[: requested_uri.rindex("/")], 'register_name' : registry_label, 'register' : requested_register.url  }
        except:
            vars = { 'uri' : "/".join((requested_register.url,requested_uri)) , 'server' : binding.service_location , 'path' : requested_uri, 'term' : requested_uri , 'path_base' : requested_uri, 'register_name' : registry_label, 'register' : requested_register.url  }
    else:
        vars = { 'uri' : requested_register.url , 'server' : binding.service_location , 'path' : requested_uri, 'term' : '' , 'path_base' : '' , 'register_name' : registry_label, 'register' : requested_register.url  }
    
    
    # Convert the URL template to a resolvable URL - passing context variables, query param values and headers) 
    url = rule.resolve_url_template(requested_uri, url_template, vars, request.GET  )
    
    # Perform the redirection if the resolver returns something, or a 404 instead
    if url:
        return HttpResponseSeeOther(url)
    else:
        return HttpResponseNotFound('The requested URI did not return any document')

