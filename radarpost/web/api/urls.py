from routes.route import Route

slug_req = {'mailbox_slug': '[a-z0-9_]{1,128}'}
api = "radarpost.web.api.controller"

routes = [
    Route("feeds_opml", "/{mailbox_slug}/feeds.opml",
          action="feeds_opml", controller=api, requirements=slug_req),

    Route("atom_feed", "/{mailbox_slug}/atom.xml",
          action="atom_feed", controller=api, requirements=slug_req),

    Route("mailbox_rest", "/{mailbox_slug}",
          action="mailbox_rest", controller=api, requirements=slug_req),
]
