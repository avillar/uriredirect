from django.http import HttpResponse, HttpResponseNotFound, HttpResponseServerError, HttpResponsePermanentRedirect, HttpResponseNotAllowed
from django.core.exceptions import ObjectDoesNotExist
from uriredirect.models import UriRegister
from uriredirect.http import HttpResponseNotAcceptable, HttpResponseSeeOther
import re
import json

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

def qordered_prefs(prefstring):
    qprofs= [x.strip() for x in prefstring.split(',')]
    profile_qs = {}
    for qprof in qprofs:
        parts = [x.strip() for x in qprof.split(';')]
        prof = parts[0]
        if prof[0] == '<':
            prof = prof[1:-1]
        profile_qs[prof]=1 # default value
        for p in parts[1:]:
            kvp= [x.strip() for x in p.split('=')]
            if kvp[0] == 'q':
                profile_qs[prof]=kvp[1]
    return sorted( profile_qs, key=profile_qs.get )    
        
        
def resolve_uri(request, registry_label, requested_uri, requested_extension):
    if request.META['REQUEST_METHOD'] == 'GET':
        req=request.GET
        head=False
    elif request.META['REQUEST_METHOD'] == 'HEAD':
        req=request.GET
        head=True
    else:
        return HttpResponseNotAllowed([request.META['REQUEST_METHOD']])
        
    if requested_extension :
        requested_extension = requested_extension.replace('.','')
    debug = False 
    
    try:
        if req['pdb'] :
            import pdb; pdb.set_trace()
    except:
        pass
    try:
        if req['debug'] :
            debug=True
    except: pass
    
    try:
        profile_prefs = qordered_prefs(request.META['HTTP_ACCEPT_PROFILE'])
            
    except:
        profile_prefs = None
        
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
        if requested_register and registry_label:
            # register but no rules, so havent joined yest 
            requested_uri = "/".join( (registry_label, "" if requested_uri == '/' else requested_uri )) if requested_uri else registry_label
        rulechains = default_register.find_matching_rules(requested_uri) 
        requested_register= default_register
        if len(rulechains) == 0:
            return HttpResponseNotFound('The requested URI base does not match base URI pattern for any rewrite rules')
 
    # at this point we have all the URIs that match the bnase URI - thats enough to list the available profiles for the base resource
    if requested_register.url:
        register_uri_base = requested_register.url
    else:
        host_base = "://".join((request.scheme,request.get_host()))   
        register_uri_base = "".join((host_base,request.path[:request.path.index(registry_label)-1]))
           
    
    # now to resolve redirect we need to find subset of rules matching viewname, and other query param constraints

    rule = None # havent found anything yet until we check params
    matched_profile = None
    content_type = None
    clientaccept = request.META.get('HTTP_ACCEPT', '*')
    # note will ignore accept header and allow override format/lang in conneg if LDA convention in use
       
    for rulechain in rulechains :
        binding = rulechain[0] 
        for patrule in rulechain[1:] :
            (use_lda, ignore) = patrule.get_prop_from_tree('use_lda')
            if use_lda :
                try:
                    requested_extension= req['_format']
                except : pass
                if requested_extension :
                    accept = None
                else :
                    accept = clientaccept # allow content negotiation only if not specified
            else :
                accept = clientaccept
            # check query string args before HTTP headers
            #(matchpatterns, prule) = patrule.get_prop_from_tree('view_pattern')
            matchpatterns = patrule.view_pattern
            if matchpatterns :
                viewprops = getattr(patrule,'view_param') # prule ?
                if not viewprops :
                    HttpResponseServerError('profile match pattern set but the query parameter to match is not set for rule %s' % patrule)
                else:
                    for viewprop in re.split(',|;',viewprops) :
                        try:
                            requested_view = req[viewprop]
                            break
                        except:
                            requested_view = None
                    viewpats = re.split(',|;',matchpatterns)
                    for viewpat in viewpats :                      
                        if ((viewpat == "") and not requested_view) or ( requested_view and re.match(requested_view,viewpat)):
                            url_template,content_type = patrule.get_url_template(requested_extension, accept)
                            if url_template :
                                rule = patrule 
                            break
                    
                    if rule:
                        break
            elif patrule.profile.exists() :
                # may be set in header - but try to match query string arg with profile first
                                   
                rplist = getattr(patrule,'view_param') 
                requested_profile = None
                matched_profile = None
                if rplist:
                    for rp in re.split(',|;',rplist):
                        try: 
                            requested_profile_list = req[rp]
                        except:
                            continue
                        for requested_profile in qordered_prefs(requested_profile_list):
                            for p in patrule.profile.all() :
                                if( requested_profile in p.token.split(',')):
                                    matched_profile = p
                                else:
                                    for toklist in p.profilesTransitive.values_list('token', flat=True):
                                        if( requested_profile in toklist.split(',')):
                                            matched_profile = p
                                   
                                if matched_profile :
                                    url_template,content_type = patrule.get_url_template(requested_extension, accept)
                                    if url_template :
                                        rule = patrule
                                        break;
                            if rule:
                                break ;
                if not rule and not requested_profile and profile_prefs:
                    for rp in profile_prefs :
                        for p in patrule.profile.all() :
                            if( p.uri==rp):
                                matched_profile = p
                            else:
                                try:
                                    matched_profile = p.profilesTransitive.get(uri=rp)
                                except:
                                    matched_profile = None
                            if matched_profile :
                                print "found token matching profile %s " % (p,)
                                url_template,content_type = patrule.get_url_template(requested_extension, accept)
                                if url_template :
                                    rule = patrule
                                    matched_profile=p
                                    break
                        if matched_profile:
                            break
                                    
            elif not rule :  # if no specific query set, then set - otherwise respect any match made by the more specific rule
                url_template,content_type = binding.get_url_template(requested_extension, accept)
                if url_template :
                    rule = patrule
        if rule :
            break
 
    vars = { 
        'uri_base' : "://".join((request.scheme,request.get_host())) ,
        'server' : binding.service_location.replace("http",request.scheme,1) if binding.service_location else '' ,
        'path' : requested_uri, 
        'register_name' : registry_label,
        'register' : requested_register.url.replace("http",request.scheme,1),
        'profile' : matched_profile.token if matched_profile else ''
        } 
        
    if not rule :
        response = HttpResponseNotFound('A profile for the requested URI base exists but no rules match for the requested format')
        url=None
    else:
        # print url_template 
 
 
        
        
        # set up all default variables
        if  requested_uri :
            try:
                term = requested_uri[requested_uri.rindex("/")+1:]
                vars.update({ 'uri' : "/".join((register_uri_base.replace("http",request.scheme,1) ,requested_uri)),   'term' : term , 'path_base' : requested_uri[: requested_uri.rindex("/")] })
            except:
                vars.update({ 'uri' : "/".join((register_uri_base.replace("http",request.scheme,1) ,requested_uri)) ,   'term' : requested_uri , 'path_base' : requested_uri })
        else:
            vars.update({ 'uri' : register_uri_base ,  'term' : '' , 'path_base' : ''   })
        
        
        # Convert the URL template to a resolvable URL - passing context variables, query param values and headers) 
        url = rule.resolve_url_template(requested_uri, url_template, vars, req  )
    
    proflinks = generate_links_for_profiles("/".join((register_uri_base.replace("http",request.scheme,1) ,requested_uri)), rulechains, matched_profile, content_type)
        
    # Perform the redirection if the resolver returns something, or a 404 instead
    if debug:
        response = HttpResponse("Debug mode: rule matched (%s , %s) generated %s \n\n template variables available: \n %s \n\n Link: \n\t%s" % ( rule, content_type, url, json.dumps(vars , indent = 4),'\n\t'.join( proflinks.split(',')) ),content_type="text/plain")
    elif url:
        response =  HttpResponseSeeOther(url)
    else:
        response = HttpResponseNotFound('The requested URI did not return any document')

    response.setdefault("Link",proflinks)
    if matched_profile:
        mps = "<" + matched_profile.uri + ">"
        for p in matched_profile.profilesTransitive.values_list('uri'):
            mps += ",<%s>" % p
        response.setdefault("Content-Profile", mps)
    
    return response

def generate_links_for_profiles(uri,rulechains,matched_profile,content_type):
    links = {}
    tokens = {}
    for rc in rulechains:
        for rule in rc[1:]: 
            if rule.profile :
                for prof in rule.profile.all():
                    links[prof.uri] = rule.extension_list()
                    tokens[prof.uri] = prof.token

    return ",".join( (",".join(tokenmappings(tokens)), ",".join(makelinkheaders(uri,links, matched_profile, content_type))))
    
def makelinkheaders (uri,links,matched_profile,content_type):
    proflinks= []
    for prof in links.keys():
        isprof = matched_profile and matched_profile.uri == prof
        for media_type in links[prof]:
            ismedia = media_type == content_type
            proflinks.append( '<%s>; rel="%s"; type="%s"; profile="%s"' % ( uri, 'self' if isprof and ismedia else 'alternate', media_type, prof) )
    return proflinks

def tokenmappings (tokens):
    tms= []
    for prof in tokens.keys():
        for tok in tokens[prof].split(','):
            tms.append( '<http://www.w3.org/ns/dx/prof/Profile>; rel="type"; token="%s"; anchor=<%s>' % ( tok,prof) )
    return tms
    
            
       
    
    