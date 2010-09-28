from gevent.wsgi import WSGIServer
from radarpost.web.app import make_app

default_config = {
    'apps': ['radarpost.web.radar_ui', 
             'radarpost.web.api'],
    'debug': True,
    'session.type': 'memory'
}

if __name__ == '__main__':
    app = make_app(default_config) 
    server = WSGIServer(('', 5555), app)
    server.serve_forever()