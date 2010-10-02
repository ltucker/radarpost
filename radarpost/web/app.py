import logging
from beaker.middleware import SessionMiddleware
from routes import Mapper
from routes.middleware import RoutesMiddleware
import sys
import traceback
from webob import Request, Response


from radarpost.config import CONFIG_INI_PARSER_PLUGIN, parse_bool
from radarpost.main import COMMANDLINE_PLUGIN, BasicCommand
from radarpost import plugins
from radarpost.web.context import RequestContext, build_routes


log = logging.getLogger(__name__)

def make_app(config, ContextType=RequestContext):
    """
    builds a full application stack.  These can be composed
    and configured elsewhere / differently as needed.
    """
    app = Application(config, ContextType=ContextType)
    app = RoutesMiddleware(wsgi_app=app, mapper=build_routes(config),
                           use_method_override=False, singleton=False)

    beaker_options = {}
    for k in config.keys():
        if k.startswith('beaker.session.'): 
            beaker_options[k[len('beaker.'):]] = config[k]
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
                    response = action(request)
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

DEFAULT_RADAR_PORT = 9332
class StartDevWebServer(BasicCommand):
    command_name = "serve"
    description = "start development web server"

    def setup_options(self, parser):
        parser.set_usage(r"%prog" + " %s <command> [port] [options]" % self.command_name)

    def __call__(self, config, options, args):
        if len(args) > 2: 
            self.print_usage()
            return 1
        elif len(args) == 2:
            try:
                port = int(args[1])
            except: 
                print 'Unable to parse port "%s"' % args[1]
                self.print_usage()
                return 1
        else: 
            port = DEFAULT_RADAR_PORT
            
        from gevent.wsgi import WSGIServer
        app = make_app(config) 
        server = WSGIServer(('', port), app)
        print "* serving on port %d" % port
        server.serve_forever()
plugins.register(StartDevWebServer(), COMMANDLINE_PLUGIN)