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
                   conditions={'method': ['HEAD', 'GET', 'PUT', 'POST', 'DELETE']})

    ##############

    mapper.connect("subscriptions_opml", "/{mailbox_slug}/subscriptions.opml",
                   action="subscriptions_opml", controller=api,
                   requirements=slug_req,
                   conditions={'method': ['GET', 'PUT', 'POST', 'HEAD']})

    mapper.connect("subscriptions_rest", "/{mailbox_slug}/subscriptions.json",
                   action="subscriptions_rest", controller=api,
                   requirements=slug_req,
                   conditions={'method': ['GET', 'POST']})

    mapper.connect("subscription_rest", "/{mailbox_slug}/subscriptions/{sub_slug}",
                  action="subscription_rest", controller=api,
                  requirements=slug_req,
                  conditions={'method': ['HEAD', 'GET', 'POST', 'DELETE']})



    mapper.connect("atom_feed", "/{mailbox_slug}/atom.xml",
                   action="atom_feed_latest", controller=api,
                   requirements=slug_req,
                   conditions={'method': ['GET', 'HEAD']})

    mapper.connect("message_rest", "/{mailbox_slug}/items/{message_slug}",
                   action="message_rest", controller=api, 
                   requirements=slug_req,
                   conditions={'method': ['DELETE']})

    mapper.connect("mailbox_rest", "/{mailbox_slug}",
                   action="mailbox_rest", controller=api, requirements=slug_req,
                   conditions={'method': ['HEAD', 'PUT', 'POST', 'DELETE']})
                   
    #########################
    # feed search support
    
    mapper.connect("verify_feed", "/feedsearch/feed", 
                   action="verify_feed", controller=api)
    
    mapper.connect("feed_links_html", "/feedsearch/html",
                   action="feed_links_html", controller=api)
    
    mapper.connect("feed_links_opml", "/feedsearch/opml",
                   action="feed_links_opml", controller=api)