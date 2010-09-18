from django.conf.urls.defaults import *

urlpatterns = patterns('radarpost.web.radar_api.views',
    url(r'^(?P<mailbox_slug>[a-z0-9_]{1,128})/feeds.opml/?$', 'feeds_opml', name='feeds_opml'),
    url(r'^(?P<mailbox_slug>[a-z0-9_]{1,128})/atom.xml/?$', 'atom_feed', name='atom_feed'),
    url(r'^(?P<mailbox_slug>[a-z0-9_]{1,128})/?$', 'mailbox_rest', name="mailbox_rest")
)