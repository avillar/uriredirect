from django.http import HttpResponse, HttpResponseNotFound, HttpResponseServerError, HttpResponsePermanentRedirect, HttpResponseNotAllowed
from django.core.exceptions import ObjectDoesNotExist
from uriredirect.models import UriRegister,Profile
from uriredirect.http import HttpResponseNotAcceptable, HttpResponseSeeOther
import re
import json
from rdflib import Graph,namespace
from rdflib.term import URIRef, Literal
from rdflib.namespace import Namespace,NamespaceManager,RDF, RDFS
from django.template.loader import render_to_string
from mimeparse  import best_match
from django.conf import settings

ALTR="http://www.w3.org/ns/dx/conneg/altr"
ALTRNS = Namespace("http://www.w3.org/ns/dx/conneg/altr#")
ALTR_HASREPRESENTATION = URIRef( "#".join( (ALTR,'hasRepresentation')))
ALTR_REPRESENTATION = URIRef( "#".join( (ALTR,'Representation')))
DCT = Namespace("http://purl.org/dc/terms/")
DCT_CONFORMSTO= URIRef("http://purl.org/dc/terms/conformsTo")
DCT_FORMAT= URIRef("http://purl.org/dc/terms/format")
PROF_TOKEN= URIRef("http://www.w3.org/ns/prof/token")

RDFLIBFORMATS = { 
    'application/ld+json': 'json-ld' ,
    'text/html' :'html',
    'text/turtle': 'ttl',
    'application/json': 'json-ld' ,
    'application/rdf+xml': 'xml' }

ALTR_PROFILE = None

def getALTR():
    global ALTR_PROFILE
    if not ALTR_PROFILE:
        ALTR_PROFILE,created = Profile.objects.get_or_create(token="alt", uri=ALTR, defaults={ 'label': 'alternates using W3C model' , 'comment' : 'Implements the https://www.w3.org/TR/dx-prof-conneg/ standard alternates view of available profiles and media types.' } )
    
    return ALTR_PROFILE    
    
def resolve_register_uri(request, registry_label=None,requested_extension=None):
    """
        resolve a request to the register itself - just another URI
    """
    return resolve_uri(request, registry_label, None, requested_extension )
    
def resolve_registerslash_uri(request, registry_label,requested_extension=None):
    """
        resolve a request to the register itself - with a trailing slash
    """
    return resolve_uri(request, registry_label, "/", requested_extension )

def qordered_prefs(prefstring):
    qprofs= [x.strip() for x in prefstring.split(',')]
    profile_qs = {}
    for qprof in qprofs:
        if (not qprof ) :
            continue
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
        
        
def resolve_uri(request, registry_label, requested_uri, requested_extension=None):
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
        requested_uri.replace('http:', request.headers['X-Forwarded-Proto'] + ":",1)
    except:
        pass
        
    clientaccept = request.META.get('HTTP_ACCEPT', '*')
    
    try:
        profile_prefs = qordered_prefs(request.META['HTTP_ACCEPT_PROFILE'])
            
    except:
        profile_prefs = []
        
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
    #
    # we need to find this anyway (unless we have cached it in some future enhancement - as we need to be able to spit out the alternates view
    # based on the matching rules even if we are not trying to then match a rule to the conneg parameters
    #
    rulechains = []
    if requested_register:
        rulechains = requested_register.find_matching_rules(requested_uri)
    if default_register and (not requested_register or len(rulechains) == 0) :
        if requested_register and registry_label:
            # register but no rules, so havent joined yest 
            requested_uri = "/".join( (registry_label, "" if requested_uri == '/' else requested_uri )) if requested_uri else registry_label
        rulechains = default_register.find_matching_rules(requested_uri) 
        requested_register= default_register
    if len(rulechains) == 0:
        if debug:
            return HttpResponse("Debug mode: Not register found with matching rules. \n Headers %s\n" % (  request.headers, ),content_type="text/plain") 
        else:
            return HttpResponseNotFound('The requested URI does not match any resource - no rules found for URI base')
 
    # at this point we have all the URIs that match the base URI - thats enough to list the available profiles for the base resource
    if requested_register.url:
        register_uri_base = requested_register.url
    else:
        host_base = "://".join((request.scheme,request.get_host()))   
        register_uri_base = "".join((host_base,request.path[:request.path.index(registry_label)-1]))
           
    
    # rebuild full URI
    if  requested_uri :
        uri= "/".join((register_uri_base.replace("http",request.scheme,1) ,requested_uri))
    else:
        uri= register_uri_base 

    links,tokens,labels,descs = collate_alternates(rulechains)
    
    response_body = None
    try:
        if ALTR in profile_prefs or request.GET['_profile'] == "alt" :           
            matched_profile = getALTR()
            try: 
                content_type=request.GET['_mediatype']
            except:
                content_type= best_match( RDFLIBFORMATS.keys() , clientaccept) 
            if content_type == 'text/html' :
                # call templating to turn to HTMLmake_altr_graph
                template = 'altrbase.html'
                try:
                    template = settings.URIREDIRECT_ALTR_BASETEMPLATE
                except:
                    pass
                response_body= render_to_string('altr.html', { 'page_template': template, 'links':links, 'uri':uri, 'tokens':tokens, 'labels':labels, 'descs':descs , 'stylesheets': [] })
            else:
                response_body = make_altr_graph (uri,links,tokens,labels,RDFLIBFORMATS[content_type])
    except Exception as e:
        print (e)
        pass
    
    if not response_body:     
        # now to resolve redirect we need to find subset of rules matching viewname, and other query param constraints
        rule,matched_profile,content_type,exception,url,substitutable_vars = match_rule( request , uri, rulechains, requested_register, register_uri_base, registry_label, requested_uri, profile_prefs, requested_extension,clientaccept) 
    else:
        rule=None
        substitutable_vars= None
        url=None
        
    #import pdb; pdb.set_trace()    
    proflinks = generate_links_for_profiles("/".join(filter(None,(register_uri_base.replace("http",request.scheme,1) ,requested_uri))), links, tokens, matched_profile, content_type)
        
    # Perform the redirection if the resolver returns something, or a 404 instead
    if debug:
        response = HttpResponse("Debug mode: rule matched (%s , %s) generated %s \n\n template variables available: \n %s \n\n Link: \n\t%s\n\n Body \n%s \nHeaders %s\n" % ( rule, content_type, url, json.dumps(substitutable_vars , indent = 4),'\n\t'.join( proflinks.split(',')), response_body, request.headers ),content_type="text/plain")
    elif response_body:
        response = HttpResponse(response_body,content_type=content_type) 
    elif url:
        response =  HttpResponseSeeOther(url)
    elif exception:
        response = HttpResponseNotFound(exception)
    else:
        response = HttpResponseNotFound('The requested URI did not return any document')


    if matched_profile:
        mps = "<" + matched_profile.uri + ">"
        for p in matched_profile.profilesTransitive.values_list('uri'):
            mps += ",<%s>" % p
        response.setdefault("Content-Profile", mps)
    response.setdefault('Access-Control-Allow-Origin', '*' )
    response.setdefault("Link",proflinks)    
    return response

def match_rule( request, uri, rulechains,requested_register,register_uri_base,registry_label, requested_uri, profile_prefs, requested_extension ,clientaccept ): 
    rule = None # havent found anything yet until we check params
    matched_profile = None
    content_type = None
    exception = None
    # note will ignore accept header and allow override format/lang in conneg if LDA convention in use
       
    for rulechain in rulechains :
        if rule:
            break
        binding = rulechain[0] 
        for patrule in rulechain[1:] :
            if rule:
                break
            (use_lda, ignore) = patrule.get_prop_from_tree('use_lda')
            if use_lda :
                try:
                    requested_extension= request.GET['_format']
                except : 
                    try:
                        requested_extension= request.GET['_mediatype']
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
                    exception = 'resource matches pattern set but the query parameter to match is not set for rule %s' % patrule
                    return (rule,matched_profile,content_type,exception)
                else:
                    for viewprop in re.split(',|;',viewprops) :
                        try:
                            requested_view = request.GET[viewprop]
                            break
                        except:
                            requested_view = None
                    viewpats = re.split(',|;',matchpatterns)
                    for viewpat in viewpats :                      
                        if ((viewpat == "") and not requested_view) or ( requested_view and re.match(requested_view,viewpat)):
                            url_template,content_type,default_profile = patrule.get_url_template(requested_extension, accept)
                            if url_template :
                                rule = patrule
                                matched_profile = default_profile
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
                            requested_profile_list = request.GET[rp]
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
                                    url_template,content_type,default_profile = patrule.get_url_template(requested_extension, accept)
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
                                url_template,content_type,default_profile = patrule.get_url_template(requested_extension, accept)
                                if url_template :
                                    rule = patrule
                                    matched_profile=p
                                    break
                        if rule:
                            break
                                    
            elif not rule :  # if no specific query set, then set - otherwise respect any match made by the more specific rule
                url_template,content_type,profile = binding.get_url_template(requested_extension, accept)
                if url_template :
                    rule = patrule

 
    vars = { 
        'uri_base' : "://".join((request.scheme,request.get_host())) ,
        'server' : binding.service_location.replace("http:",request.scheme+":",1) if binding.service_location else '' ,
        'server_http' : binding.service_location.replace("https:","http:",1) if binding.service_location else '' ,
        'server_https' : binding.service_location.replace("http:","https:",1) if binding.service_location else '' ,
        'path' : requested_uri, 
        'register_name' : registry_label,
        'register' : requested_register.url.replace("http",request.scheme,1),
        'profile' : matched_profile.token if matched_profile else ''
        } 
        
    if not rule :
        exception = 'A profile for the requested URI base exists but no rules match for the requested format'
        url=None
    else:
        # print url_template 
 
 
        
        
        # set up all default variables
        if  requested_uri :
            try:
                term = requested_uri[requested_uri.rindex("/")+1:]
                vars.update({ 'uri' : uri,   'term' : term , 'path_base' : requested_uri[: requested_uri.rindex("/")] })
            except:
                vars.update({ 'uri' : uri ,   'term' : requested_uri , 'path_base' : requested_uri })
        else:
            vars.update({ 'uri' : register_uri_base ,  'term' : '' , 'path_base' : ''   })
        
        
        # Convert the URL template to a resolvable URL - passing context variables, query param values and headers) 
        url = rule.resolve_url_template(requested_uri, url_template, vars, request  )
    
    return rule,matched_profile,content_type,exception, url, vars 
    
def generate_links_for_profiles(uri,links,tokens,matched_profile,content_type):
    """ Generate the set of link headers and token mappings for a set of rulechains for a resource uri
    
    returns {links} and {tokens} dicts - keys are profile URI 
    """
    return ",".join( (",".join(tokenmappings(tokens)), ",".join(makelinkheaders(uri,links,tokens, matched_profile, content_type))))  
    
def collate_alternates(rulechains):
    """ Collate available representations 
    
    cachable collation of links and token mappings for a set of resolving rules that determine what resources are available.
    Always add W3C canonical ALTR view
    """
    links = { ALTR : RDFLIBFORMATS.keys() }
    tokens = { ALTR: 'alt'}
    labels ={ ALTR: getALTR().label}
    descs = {ALTR: getALTR().comment}
    for rc in rulechains:
        for rule in rc[1:]: 
            if rule.profile :
                for prof in rule.profile.all():
                    links[prof.uri] = rule.extension_list()
                    tokens[prof.uri] = prof.token
                    labels[prof.uri] = prof.label if prof.label else prof.uri
                    descs[prof.uri] = prof.comment
    return links,tokens,labels,descs

    
def makelinkheaders (uri,links,tokens,matched_profile,content_type):
    """ make a serialisation of available profiles in Link Header syntax """
    proflinks= []
    if matched_profile:
        proflinks = ['<%s>; rel="profile" ; anchor=<%s>' % (matched_profile.uri, uri)]
    for prof in links.keys():
        isprof = matched_profile and matched_profile.uri == prof
        for media_type in links[prof]:
            ismedia = media_type == content_type
            proflinks.append( '<%s>; rel="%s"; type="%s"; profile="%s"' % ( uri, 'self' if isprof and ismedia else 'alternate', media_type, prof) )
    return proflinks

def make_altr_graph (uri,links,tokens,labels,content_type):
    """ make a serialisation of the altR model for W3C list_profiles using content type requested """
    gr = Graph()
    nsgr = NamespaceManager(gr)
    nsgr.bind("altr", ALTRNS)
    nsgr.bind("dct", DCT)
    id = URIRef(uri)
    for prof in links.keys():
        puri = URIRef(prof)
        rep = URIRef( "?_profile=".join((uri, tokens[prof])))
        gr.add( (id, ALTR_HASREPRESENTATION , rep) )
        gr.add( (puri, RDFS.label , Literal(labels[prof])) )
        gr.add( (rep, DCT_CONFORMSTO , puri) )
        gr.add( (rep, RDF.type , ALTR_REPRESENTATION) )
        gr.add( (rep, PROF_TOKEN , Literal(tokens[prof])) )
        for media_type in links[prof]:
            gr.add( (rep, DCT_FORMAT , Literal( media_type)) )
    return gr.serialize(format=content_type)

def tokenmappings (tokens):
    tms= []
    for prof in tokens.keys():
        for tok in tokens[prof].split(','):
            tms.append( '<http://www.w3.org/ns/dx/prof/Profile>; rel="type"; token="%s"; anchor=<%s>' % ( tok,prof) )
    return tms
    
            
       
    
    