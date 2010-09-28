import logging
from beaker.middleware import SessionMiddleware
from routes import Mapper
from routes.middleware import RoutesMiddleware
import sys
import traceback
from webob import Request, Response


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
        if k.startswith('session.'): 
            beaker_options[k] = config[k]
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