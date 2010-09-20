import logging
from routes import Mapper
from routes.middleware import RoutesMiddleware
import sys
import traceback
from webob import Request, Response

from radarpost import settings
from radarpost.web.helpers import build_routes

log = logging.getLogger(__name__)

def make_app():
    app = Application()
    app = RoutesMiddleware(wsgi_app=app, mapper=build_routes(),
                           use_method_override=False, singleton=False)
    return app

class Application(object):

    def __call__(self, environ, start_response):
        try:
            route = environ.get('wsgiorg.routing_args')            
            if route is None:
                response = Response(status=404)
            else:
                action = _get_action(route[1])
                response = action(Request(environ=environ))
        except:
            response = Response(status=500)
            ex_text = traceback.format_exc()
            log.error("Unexpected error: %s" % ex_text)
            if getattr(settings, 'DEBUG', False) == True:
                response.body = ex_text
                response.content_type = 'text/plain'

        return response(environ, start_response)

def _get_action(match):
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