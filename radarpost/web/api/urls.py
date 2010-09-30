slug_req = {'mailbox_slug': '[a-z0-9_]{1,128}'}
userid_req = {'userid': '[a-zA-Z0-9_]{1,64}'}
api = "radarpost.web.api.controller"

def add_routes(mapper):
    
    ##############

    mapper.connect("login", "/login",
                   action="login", controller=api,
                   conditions={'method': ['POST']})

    mapper.connect("logout", "/logout",
                   action="logout", controller=api,
                   conditions={'method': ['POST']})

    mapper.connect("current_user_info", "/user",
                   action="current_user_info", controller=api,
                   conditions={'method': ['GET', 'HEAD']})

    mapper.connect("create_user", "/user",
                   action="create_user", controller=api,
                   conditions={'method': ['POST']})

    mapper.connect("user_rest", "/user/{userid}",
                   action="user_rest", controller=api,
                   requirements=userid_req,
                   conditions={'method': ['GET', 'PUT', 'POST', 'HEAD', 'DELETE']})

    ##############

    mapper.connect("feeds_opml", "/{mailbox_slug}/feeds.opml",
                   action="feeds_opml", controller=api, 
                   requirements=slug_req,
                   conditions={'method': ['GET', 'PUT', 'POST', 'HEAD']})

    mapper.connect("atom_feed", "/{mailbox_slug}/atom.xml",
                   action="atom_feed_latest", controller=api,
                   requirements=slug_req,
                   conditions={'method': ['GET', 'HEAD']})

    mapper.connect("mailbox_rest", "/{mailbox_slug}",
                   action="mailbox_rest", controller=api, requirements=slug_req,
                   conditions={'method': ['HEAD', 'POST', 'DELETE']})