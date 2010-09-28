slug_name_pat = '[a-z0-9_]{1,128}'
slug_req = {'mailbox_slug': slug_name_pat}
ui = "radarpost.web.radar_ui.controller"

def add_routes(mapper):
    mapper.connect("login_page", "/login",
                   action="login", controller=ui,
                   conditions={'method': ['GET']})

    mapper.connect("logout_page", "/logout",
                   action="logout", controller=ui,
                   conditions={'method': ['GET']})
                   
    mapper.connect("signup", "/signup", 
                   action="signup", controller=ui)

    mapper.connect("front_page", "/",
                   action="front_page", controller=ui)

    mapper.connect("create_mailbox_ui", "/create",
                   action="create_mailbox", controller=ui)

    mapper.connect("list_mailboxes", "/index",
                   action="list_mailboxes", controller=ui)

    mapper.connect("view_mailbox", "/{mailbox_slug}",
                   action="view_mailbox", controller=ui,
                   requirements=slug_req,
                   conditions={'method': ['GET']})