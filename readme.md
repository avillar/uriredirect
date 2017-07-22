# URI Redirection Engine

## What does it do?
- Uses rules to bind URIs with parameters to service endpoints using templated URL patterns.
- Allows you to put together a list of rewrite rules, very similar to Apache's mod_rewrite, except the rules are persisted in a database, and Django provides a great administration interface.
- Allows rules to inherit and override or extend parent rules, creating a flexible capability to desribe and bind to complex APIs with many optional parameters.
- Supports re-usable "API rules", so standard APIs and Linked Data best practices can be implemented simply by binding a URI base (namespace) to the APIs deployed to service it.
- allows specific rules to override default bindings for URL parameters (e.g. Linked Data _\_view_ parameter to choose specific content profile to return (in addition to MIME type encoding choice via HTTP Content-Type headers)

## Rules
- Your rewrite rules specify a regular expression pattern. Incoming URI requests are matched against these patterns, and the matching rule determines the destination of the request.
- You write out the URLs that URIs should redirect to much as you would in Apache's mod_rewrite, using $1, $2 notation to indicate capture groups in the regular expression that should be used as part of the redirect location.
- For each rewrite rule, you can specify multiple representations. The server performs HTTP Content Negotiation on incoming URI requests and uses your content-mappings to send a request with a specific Accept header to the appropriate redirect location.
- Groups rewrite rules into URI Registers. Your server can "serve" any number of URI registers, and might know about other, remote registries. If your server recieves a URI request for a URI register that it knows about, but does not serve itself, that request is forwarded to the remote server.
- rules may inherit from one or more parents, in which case they supply additional rules or overwrite defaults in inherited rules
- leaving the URI register and matching pattern blank creates an abstract "API binding" that can be re-used for many registers

## What gets persisted:
### URI Registries
*models/UriRegister.py*
- label: a short label that identifies this URI register in a URI
- url: an absolute URL for a server that can resolve this register's URIs. If this is a remote URL (not on this server), URI requests to this server will be forwarded to this URL.
- can_be_resolved: True if URIs that are part of this register can be resolved by this server.

Generally, the first thing you'd want to do is set up a register that your server can resolve.
At `http://your server name}/admin/uriredirect/uriregister/add/` give your register a label and a URL (`http://{your server name}/`). Check the `Can be resolved` box

### Rewrite Rules
*models/RewriteRule.py*
- register: Foreign key to the register to which this rewrite rule belongs (if absent then a re-usable API description)
- label: A simple label for this rewrite rule. Helps you find it in Django's admin interface.
- description: An optional description of the rewrite rule.
- parent: Optional rule to inherit from (either an API binding, or a ruleset extending an API specification)
- pattern: the regular expression pattern for an incoming URI request that this rule should match. 
- Use LDA standard params: a flag to automatically bind overrides for HTTP content headers from URL params "\_format" and "\_lang"
- View param: optional name of a parameter that defines a specific view, to which these specific rules will apply
- view pattern: regex pattern to recognise the view name in the designated view parameter
- Accept-mapping: A many-to-many relationship with media types. Each representation of your resource has a specific mime type and is accessed at a specific URL.

When generating a rewrite rule, there are two things to keep in mind:
- a URI coming into the system will be in this general structure: `/{register label}/{part of the URI that is matched to the rule's pattern}`. That is, don't include the register label part of the URI in a rule's pattern.
- Each rule can have many representations. You should, however, make sure that you don't create two different representations (Accept-mappings in Django's admin interface) for the same media type.

### Media Types
*models/MediaType.py*
- mime_type: The MIME type for this kind of media
- file_extension: A file extension commonly used for this kind of media

### Accept Mappings
*models/AcceptMapping.py*
- rewrite_rule: Foreign key to the rewrite rule to which this mapping pertains
- media_type: Foreign key to the media type that this mapping implements
- redirect_to: A URL or URL template that represents the absolute location of a resource of the specified media type

This is simply the correlation table that handles the many-to-many relationship between rewrite rules and media types.

## At a high-level, how does it work?
1. An incoming URI request reaches the server and is handled by the `resolve_uri` function defined in *views/Resolver.py*.
2. If the request URI looks like this `http://{your server name}/{something}/{some more stuff}/`, then `{something}` is treated as the label for a particular URI register.
3. The server's list of URI registers is searched for a match to the label provided in the requested URI. There are three possible outcomes:
	- *There is no match*: The server returns a 404 error. It does not know how to resolve the request.
	- *There is a match, but it is marked as a URI register that this server cannot resolve*: A 301 response forwards the requesting client to the remote registry by its specified URL.
	- *There is a match, and this server can resolve it*: We move on...
4. The URI register is searched for a rewrite rule with a regular expression pattern that matches the `{some more stuff}` part of the requested URI. Again, three possible outcomes:
	- *There is no match*: The server returns a 404 error. There is no matching rule for the requested URI.
	- *There are multiple matching rules*: The server returns a 500 error. Someone has misconfigured the server so that it cannot uniquely identify the requested URI.
	- *There is one matching rule*: We move on...
5. The request's Accept header is checked against the list of available media types for this particular rewrite rule.
	- *There is no acceptable media type to fit the request*: The server returns a 406 error. It cannot provide an appropriate representation of the requested URI.
	- *There is more than one mapping that provides an acceptable media type*: The server returns a 500 error. Someone has misconfigured the rule so that one media type has multiple redirect locations associated with it.
	- *There is one acceptable media type that fits the request*: We move on...
6. The request's `{some more stuff}` part is matched against the rule's regular expression pattern. If the redirection location is a URL template, $1, $2, etc are replaced in the URL template with groups captured from the regular expression match.
7. An absolute URL has been constructed, and the server returns a 303 response which sends the requesting client to the appropriate location.

## What is the project's layout?
- *admin*: Contain classes that expose this project's data nicely in Django's administration interface.
- *fixtures*: Contains .json files that are used in various unit tests.
- *http*: Contains some simple HTTP helper classes.
- *models*: Contains the data models for the project. These translate to the tables that are persisted in the database.
- *tests*: Contains classes to perform unit testing on functions defined throughout the project. Run tests with `manage.py test uriredirect`.
- *views*: Contains modules and functions that respond to HTTP requests. Right now there is only the `resolve_uri` function in the `Resolver.py` module.
- *urls.py*: Contains a URL capture rule that sends HTTP requests to the `resolve_uri` function.
- *other files not really worth mentioning*

## Prerequisites
- A functioning Django environment.
- The [mimeparse](http://code.google.com/p/mimeparse/) Python module. Simple installation: `easy_install mimeparse`

## Installation
- Clone this repository to a location on your python-path or to the right place within [the layout of your Django project](https://docs.djangoproject.com/en/dev/releases/1.4/#updated-default-project-layout-and-manage-py).
- Add `uriredirect` to your list of `INSTALLED_APPS` in your Django project's `settings.py` file.
- Add a URL to your project's `urls.py` file that will send requested traffic to the app. Think about this. If...
	- You want to resolve URIs in a structure like `http://{domain name}/{register}/{identifier}/`, then you'll need the application exposed at the server's root level, something like `url(r'^', include('uriredirect.urls'))`.
	- You want to resolve URIs in a structure like `http://{domain name}/{some fixed value}/{register}/{identifier}/`, then you'll use something like `url(r'^{that fixed value}/', include('uriredirect.urls'))`.
- Run `manage.py syncdb`.
