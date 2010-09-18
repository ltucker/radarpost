from django.conf import settings
from django.conf.urls.defaults import *

urlpatterns = patterns('radarpost.web.radar_ui.views',
    url(r'^$', 'front_page', name='front_page'),
    url(r'^create/?$', 'create_mailbox', name='create_mailbox'),
    url(r'^index/?$', 'list_mailboxes', name='list_mailboxes'),
    url(r'^(?P<mailbox_slug>[a-z0-9_]{1,128})/?$', 'view_mailbox', name='view_mailbox'),
)

# rig in static media for development
if settings.DEBUG:
    import os
    static_loc = os.path.dirname(__file__)
    static_loc = os.path.join(static_loc, 'static')
    static_loc = os.path.abspath(static_loc)
    urlpatterns = patterns('',
        url(r'^static/radar/(?P<path>.*)$', 
            'django.views.static.serve',
            {'document_root': static_loc},
            name="static_file")) + urlpatterns
else:
    # these files should be mapped in and hosted elsewhere, 
    # but in order to provide a reverse url, we map in a 
    # dummy view.  If this url is reached, it always returns
    # a 404.
    urlpatterns = patterns('',
        url(r'^static/radar/(?P<path>.*)$', 
            'radarpost.web.radar_ui.views.always_404',
            name="static_file")) + urlpatterns