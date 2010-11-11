import base64
from couchdb import Server, ResourceNotFound
from hashlib import md5
from jinja2 import Environment
from jinja2.loaders import ChoiceLoader, PackageLoader
import logging
import mimetypes
import os
from pytz import timezone, utc
import routes
from routes.route import Route
import sys
import traceback
from webob import Response as HttpResponse
from webob.etag import ETagMatcher

from radarpost import plugins
from radarpost.plugins import plugin
from radarpost.mailbox import iter_mailboxes as _iter_mailboxes
from radarpost.user import User, AnonymousUser

__all__ = ['RequestContext', 'build_routes', 'config_section',
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
        self._current_user = None
        
    def url_for(self, *args, **kw):
        return self.request.environ['routes.url'](*args, **kw)

    def get_template(self, template_name):
        return self.template_env.get_template(template_name)

    def render(self, template_name, *args, **kw):
        return self.get_template(template_name).render(*args, **kw)
    
    ###########################################
    #
    # Session and Logged in User 
    #
    ###########################################
    @property
    def session(self):
        return self.request.environ['beaker.session']

    USER_SESSION_KEY = 'user_id'
    @property
    def user(self):
        """
        Property that returns the currently logged in user
        """

        if self._current_user is None and self.USER_SESSION_KEY in self.session:
            try:
                user_id = self.session[self.USER_SESSION_KEY]
                udb = self.get_users_database()
                self._current_user = User.load(udb, user_id)
            except ResourceNotFound:
                # non-existant user, wipe this session
                self.session.invalidate()

        if self._current_user is None:
            self._current_user = AnonymousUser() 
        
        return self._current_user
    
    def set_request_user(self, user):
        """
        sets the user for this request to the user specified. 
        This does not affect the user referenced in the session.
        """
        self._current_user = user
    
    def set_session_user(self, user):
        """
        Change the currently logged in user. None may be 
        specified to clear the current user.  In all 
        cases, the current session is invalidated.
        """
        self.session.invalidate()
        if user is not None and not user.is_anonymous(): 
            self.session[self.USER_SESSION_KEY] = user.id
            self.session.save()
        self._current_user = user


    ###########################################
    #
    # couchdb and database helpers
    #
    ###########################################
    
    def get_couchdb_server(self):
        """
        get a connection to the configured couchdb server. 
        """
        return get_couchdb_server(self.config)

    def get_users_database(self):
        return get_users_database(self.config, couchdb=self.get_couchdb_server())


    ##########################################
    #
    # Mailbox helper aliases 
    # these all use the config given to the 
    # RequestContext at construction time
    # 
    #########################################


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

################################

def app_ids(config):
    """
    iterate the base app module names that are 
    specified in the current configuation.
    """
    return config['web.apps']

def config_section(section, config, reprefix=''):
    if not section.endswith('.'):
        section = section + '.'
    section_options = {}
    for k in config.keys():
        if k.startswith(section): 
            section_options[reprefix + k[len(section):]] = config[k]
    return section_options

###################################
#
# Per-request HTTP Auth
#
###################################

class BadAuthenticator(Exception):
    pass

def check_http_auth(request):
    if request.authorization:
        ctx = request.context
        try:
            meth, params = request.authorization
            if meth.lower() == 'basic':
                username, password = base64.b64decode(params).split(':')
                udb = ctx.get_users_database()
                user = User.get_by_username(udb, username)
                if user is not None and user.check_password(password) == True:
                    ctx.set_request_user(user)
                    return
        except:
            pass
        raise BadAuthenticator()

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
        self.request = request
        for proc in plugins.get(TEMPLATE_CONTEXT_PROCESSORS):
            proc(request, self)

def render_to_response(template_name, template_context):
    ctx = template_context.request.context
    return HttpResponse(ctx.get_template(template_name).render(template_context))

def _make_template_env(config):
    loader = ChoiceLoader([
        PackageLoader(package) for package in app_ids(config)
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
    
@plugin(TEMPLATE_FILTERS)
def pretty_date(date, tz):
    if date.tzinfo is None: 
        date = date.replace(tzinfo=utc)
    loc = date.astimezone(timezone(tz))
    fmt = "%a, %b %d %Y at %I:%M%p %Z"
    return loc.strftime(fmt)

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
    ctx['url_for'] = request.context.url_for


@plugin(TEMPLATE_CONTEXT_PROCESSORS)
def expose_timezone(request, ctx):
    """
    exposes the variable 'TIME_ZONE' with the name
    of the configured time zone to templates.
    """
    ctx['TIME_ZONE'] = request.context.config['timezone']

#####################################
# URL Routing & Static Files
#####################################

def build_routes(config):
    router = routes.Mapper() #controller_scan=None)

    for app_module in app_ids(config):
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
                urls.add_routes(router)
            except AttributeError:
                continue
        except:
            log.error("Error loading app urls for '%s': %s" % 
                      (app_module, traceback.format_exc()))
            raise

        # introduce a route that allows reverse mapping a static file
        # url based on the configuration.  In debug mode, we'll serve
        # the files, but it is expected that in production actual file 
        # hosting is handled by a separate web server or configured 
        # as middleware.  In this case, if the route is ever reached, 
        # the result is 404.
        #
        # the main purpose of having this route in either case is to be 
        # able to call context.url_for('static_file', 'some/file/name.js') and 
        # return the appropriate url based on the configuration.
        # 
        static_url = config['web.static_files_url']
        if config['web.debug'] == False:
            router.connect('static_file', '%s{path:.*?}' % static_url,
                           action="always_404", controller='radarpost.web.context')
        else:
            router.connect('static_file', '%s{path:.*?}' % static_url,
                           action="serve_static_file", controller='radarpost.web.context')
            
    return router

def static_file_paths(config):
    static_paths = []
    for app_module in app_ids(config):
        try:
            __import__(app_module)
            app_base = os.path.dirname(sys.modules[app_module].__file__)
            static_dir = os.path.join(app_base, 'static')
            if os.path.isdir(static_dir):
                static_paths.append(static_dir)
        except: 
            pass
    return static_paths

def always_404(request, *args, **kw):
    return HttpResponse(status=404)


def serve_static_file(request, path):
    """
    this is a crappy static file serving function. 
    it should not be used in production, only for 
    development and debugging!
    """
    for base_path in static_file_paths(request.context.config):
        path = os.path.normpath(path)
        filename = os.path.abspath(os.path.join(base_path, path))
        if not filename.startswith(base_path):
            continue
        if not os.path.isfile(filename): 
            continue

        # it's there....
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        try:
            return HttpResponse(open(filename, 'rb').read(), content_type=content_type)
        except: 
            continue
    return HttpResponse(status=404)

###################

def get_mailbox_etag(mailbox):
    """
    generate a string that uniquely identifies the current
    state of the given mailbox.
    """
    info = mailbox.info()
    # digest of "dbname@update_seq"
    return md5("%s@%d" % (info['db_name'], info['update_seq'])).hexdigest()

def check_etag(request, etag):
    """
    returns a response if the request contains an if-none-match 
    header that matches the given etag.  returns None if the 
    request should proceed as normal. 
    """
    
    rtags = request.headers.get('if-none-match', None)
    if rtags is None: 
        return None
    
    # spec requires that only GET and HEAD may be used
    if request.method not in ['GET', 'HEAD']: 
        return HttpResponse(status=412) # precondition failed

    matcher = ETagMatcher.parse(rtags)
    if etag in matcher:
        return HttpResponse(status=304, headers=[('etag', etag)])
    else: 
        return None

##########################################
#
# Mailbox / CouchDB related helpers
#
#########################################

def get_couchdb_server(config):
    """
    get a connection to the configured couchdb server. 
    """
    return Server(config['couchdb.address'])

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


def get_mailbox_db_prefix(config):
    """
    gets the configured name prefix for all couchdb databases 
    representing mailboxes.
    """
    return config['couchdb.prefix']


def iter_mailboxes(config, couchdb=None):
    if couchdb is None:
        couchdb = get_couchdb_server(config)
    return _iter_mailboxes(couchdb, prefix=get_mailbox_db_prefix(config))

def get_users_database(config, couchdb = None):
    if couchdb is None:
        couchdb = get_couchdb_server(config)
    user_db = config['couchdb.users_database']
    return couchdb[user_db]

