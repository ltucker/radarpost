from couchdb import Server, ResourceNotFound
from jinja2 import Environment
from jinja2.loaders import ChoiceLoader, PackageLoader
import logging
import routes
import sys
import traceback
from radarpost import plugins
from radarpost.plugins import plugin
from radarpost.mailbox import iter_mailboxes as _iter_mailboxes

__all__ = ['RequestContext', 'build_routes',
           'get_couchdb_server', 'get_database_name', 'get_mailbox_slug',
           'get_mailbox', 'get_mailbox_db_prefix', 'iter_mailboxes',
           'TEMPLATE_FILTERS','TEMPLATE_CONTEXT_PROCESSORS']

log = logging.getLogger(__name__)


class RequestContext(object):
    """
    A RequestContext represents the current configuration during a 
    request.  It is accessable as request.context when processing 
    a request.
    
    RequestContext provides a variety of helper functions for 
    working with configured templates and databases.  
    """

    def __init__(self, request, config):
        self.request = request
        self.config = config
        self.template_env = _make_template_env(config)

    def url_for(self, *args, **kw):
        return self.request.environ['routes.url'](*args, **kw)

    def get_template(self, template_name):
        return self.template_env.get_template(template_name)

    def render(self, template_name, *args, **kw):
        return self.get_template(template_name).render(*args, **kw)


    ##########################################
    #
    # Mailbox helper aliases 
    # these all use the config given to the 
    # RequestContext at construction time
    # 
    #########################################
    
    def get_couchdb_server(self):
        """
        get a connection to the configured couchdb server. 
        """
        return get_couchdb_server(self.config)

    def get_database_name(self, mailbox_slug):
        """
        get the database name corresponding to the 
        given mailbox slug.
        """
        return get_database_name(self.config, mailbox_slug)

    def get_mailbox_slug(self, dbname):
        """
        get the slug for the mailbox with the 
        database name specified.
        """
        return get_mailbox_slug(self.config, dbname)


    def get_mailbox(self, mailbox_slug, couchdb=None):
        """
        get a connection to the couchdb database with the 
        given slug. 
        """
        return get_mailbox(self.config, mailbox_slug, couchdb=couchdb)


    def get_mailbox_db_prefix(self):
        """
        gets the configured name prefix for all couchdb databases 
        representing mailboxes.
        """
        return get_mailbox_db_prefix(self.config)

    def iter_mailboxes(self, couchdb=None):
        return iter_mailboxes(self.config, couchdb=couchdb)

#############################
#
# Template helpers
#
#############################

#
# plugin ids
#

TEMPLATE_FILTERS = 'radarpost.template_filters'
# any function registered with the TEMPLATE_FILTERS 
# plugin will be make available to templates as 
# a jinja2 'filter', eg: 
#
# @plugin(TEMPLATE_FILTER)
# def fooify(x):
#    return 'foo-' + x + '-foo'
#
# allows you to say: 
#
# {{ someval|fooify }}

TEMPLATE_CONTEXT_PROCESSORS = 'radarpost.template_context_processors'
# this plugin represents functions that modify 
# the template context for each request, eg expose
# some standard variables or otherwise 
# sanitize things. Registered functions should 
# accept a webob Request and a dict representing the 
# template context and modify the context in place.
#
# eg: 
# @plugin(TEMPLATE_CONTEXT_PROCESSORS)
# def include_method(request, ctx): 
#    # always expose the http 'method' into the context
#    ctx['method'] = request.method
#
# allows you to say: 
# {{method}} 
# in any template to utilize the http method for the 
# current request.


class TemplateContext(dict):
    def __init__(self, request, ctx):
        self.update(ctx)
        for proc in plugins.get(TEMPLATE_CONTEXT_PROCESSORS):
            proc(request, ctx)

def _make_template_env(config):
    loader = ChoiceLoader([
        PackageLoader(package) for package in config.get('apps', [])
    ])

    def escape_ml(template_name):
        if template_name is None:
            return False
        return (template_name.endswith('.html') or 
                template_name.endswith('.xml'))

    env = Environment(loader=loader,
                      autoescape=escape_ml,
                      extensions=['jinja2.ext.autoescape'])
    for filt in plugins.get(TEMPLATE_FILTERS):
        env.filters[filt.__name__] = filt

    return env


@plugin(TEMPLATE_FILTERS)
def rfc3339(date):
    if date is None:
        return ''
    tz_str = 'Z' # assume Zulu time
    if date.tzinfo:
        off = date.tzinfo.utcoffset(date)
        if off is not None:
            hours, mins = divmod(off.seconds/60, 60) 
            tz_str = "%+03d:%02d" % (hours, mins)
    return date.strftime("%Y-%m-%dT%H:%M:%S") + tz_str

@plugin(TEMPLATE_CONTEXT_PROCESSORS)
def expose_request(request, ctx):
    """
    makes the request available in templates
    """
    ctx['request'] = request

@plugin(TEMPLATE_CONTEXT_PROCESSORS)
def expose_url_lookup(request, ctx):
    """
    exposes a reverse url lookup method "url_for" 
    in templates.
    """
    def lookup_url(*args, **kw):
        return url_for(request, *args, **kw)

    ctx['url_for'] = lookup_url
    
#####################################
# URL Routing
#####################################

def build_routes(apps):
    router = routes.Mapper()
    for app_module in apps:
        # look for routes, fail quietly if the 
        # router is missing.
        try:
            try:
                url_module = app_module + '.urls' 
                __import__(url_module)
                urls = sys.modules[url_module]
            except ImportError:
                continue
            try:
                app_routes = urls.routes
            except AttributeError:
                continue
            router.extend(app_routes)
        except:
            log.error("Error loading app urls for '%s': %s" % 
                      (app_module, traceback.format_exc()))
            raise
    return router
    
##########################################
#
# Mailbox / CouchDB related helpers
#
#########################################

def get_couchdb_server(config):
    """
    get a connection to the configured couchdb server. 
    """
    if 'couchdb' in config: 
        return Server(config['couchdb'])
    else:
        return Server()

def get_database_name(config, mailbox_slug):
    """
    get the database name corresponding to the 
    given mailbox slug.
    """
    return '%s%s' % (get_mailbox_db_prefix(config), mailbox_slug)

def get_mailbox_slug(config, dbname):
    """
    get the slug for the mailbox with the 
    database name specified.
    """
    prefix = get_mailbox_db_prefix(config)
    if dbname.startswith(prefix):
        return dbname[len(prefix):]
    else:
        return dbname

def get_mailbox(config, mailbox_slug, couchdb=None):
    """
    get a connection to the couchdb database with the 
    given slug. 
    """

    if couchdb is None:
        couchdb = get_couchdb_server(config)
    try:
        return couchdb[get_database_name(config, mailbox_slug)]
    except ResourceNotFound:
        return None

DEFAULT_COUCHDB_PREFIX = 'radar/'
def get_mailbox_db_prefix(config):
    """
    gets the configured name prefix for all couchdb databases 
    representing mailboxes.
    """
    if 'couchdb_prefix' in config:
        prefix = config['couchdb_prefix']
    else:
        prefix = DEFAULT_COUCHDB_PREFIX
    return prefix

def iter_mailboxes(config, couchdb=None):
    if couchdb is None:
        couchdb = get_couchdb_server(config)
    return _iter_mailboxes(couchdb, prefix=get_mailbox_db_prefix(config))
