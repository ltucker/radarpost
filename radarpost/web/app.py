import logging
from beaker.middleware import SessionMiddleware
from routes import Mapper
from routes.middleware import RoutesMiddleware
import sys
import traceback
from webob import Request, Response


from radarpost.config import CONFIG_INI_PARSER_PLUGIN, parse_bool, config_section
from radarpost.cli import COMMANDLINE_PLUGIN, BasicCommand, InvalidArguments
from radarpost import plugins
from radarpost.web.context import RequestContext, build_routes
from radarpost.web.context import check_http_auth, BadAuthenticator


log = logging.getLogger(__name__)

def make_app(config, ContextType=RequestContext):
    """
    builds a full application stack.  These can be composed
    and configured elsewhere / differently as needed.
    """
    app = Application(config, ContextType=ContextType)
    app = RoutesMiddleware(wsgi_app=app, mapper=build_routes(config),
                           use_method_override=False, singleton=False)

    beaker_options = config_section('beaker.session.',
                                    config, reprefix='session.')
    if len(beaker_options) > 0:
        app = SessionMiddleware(app, beaker_options)
    return app

class Application(object):

    def __init__(self, config, ContextType=RequestContext):
        self.config = config
        self.ContextType = ContextType

    def __call__(self, environ, start_response):
        try:
            route = environ.get('wsgiorg.routing_args')            
            if route is None:
                response = Response(status=404)
            else:
                action = _get_action(route[1])
                if action is None:
                    response = Response(status=404)
                else:
                    # build a request, augment it with a config context
                    request = Request(environ=environ)
                    context = self.ContextType(request, self.config)
                    request.context = context
                    check_http_auth(request)
                    response = action(request)
        except BadAuthenticator:
            response = Response(status=401)
        except:
            response = Response(status=500)
            ex_text = traceback.format_exc()
            log.error("Unexpected error: %s" % ex_text)
            if self.config.get('debug', False) == True:
                response.body = ex_text
                response.content_type = 'text/plain'

        return response(environ, start_response)

def _get_action(match):
    try:
        kwargs = dict(match)
        controller = kwargs.pop('controller')
        action = kwargs.pop('action')

        __import__(controller)
        controller = sys.modules[controller]
        action = getattr(controller, action)

        def act(request):
            return action(request, **kwargs)
        act.__name__ = action.__name__
        return act
    except KeyError:
        return None

@plugins.plugin(CONFIG_INI_PARSER_PLUGIN)
def parse_web_config(config):
    if 'web.apps' in config: 
        config['web.apps'] = [x.strip() for x in config['web.apps'].split(',')]
    if 'web.debug' in config:
        config['web.debug'] = parse_bool(config['web.debug'])

@plugins.plugin(CONFIG_INI_PARSER_PLUGIN)
def parse_cherrypy_config(config):
    int_opts = ['numthreads', 'max', 'request_queue_size', 'timeout', 'shutdown_timeout']    
    for k in int_opts: 
        key = 'cherrypy.%s' % k
        if key in config: 
            config[key] = int(config[key])

class RequestLogger(object):
    def __init__(self, app):
        self.app = app
        
    def __call__(self, environ, start_response):
        req_url = Request(environ).url
        def log_response(status, headers, exc_info=None):
            log.info("%s %s [%s]" % (environ['REQUEST_METHOD'], req_url, status))
            if exc_info: 
                log.error(exc_info)
            return start_response(status, headers, exc_info)
        return self.app(environ, log_response)
        
DEFAULT_RADAR_PORT = 9332
class StartDevWebServer(BasicCommand):
    command_name = "serve"
    description = "start development web server"

    @classmethod
    def setup_options(cls, parser):
        parser.set_usage(r"%prog" + " %s <command> [interface:][port] [options]" % cls.command_name)

    def __call__(self, address=None):
        """
        start development web server
        address - where to serve, [interface:]port
        """
        if address is not None:
            interface = '127.0.0.1'
            port = address
            if ':' in port:
                interface, port = port.split(':')
            try:
                port = int(port)
            except: 
                raise InvalidArguments('Unable to parse port "%s"' % address)
        else:
            interface = '127.0.0.1'
            port = DEFAULT_RADAR_PORT

        from cherrypy.wsgiserver import CherryPyWSGIServer as WSGIServer

        app = RequestLogger(make_app(self.config))
        cherry_opts = config_section('cherrypy', self.config) 
        server = WSGIServer((interface, port), app, **cherry_opts)
        
        print "* serving on %s:%d" % (interface, port)
        try:
            server.start()
        except KeyboardInterrupt:
            server.stop()        

plugins.register(StartDevWebServer, COMMANDLINE_PLUGIN)