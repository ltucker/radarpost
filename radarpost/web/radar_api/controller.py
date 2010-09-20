from couchdb import ResourceConflict
from couchdb import ResourceNotFound, PreconditionFailed
from datetime import datetime
import json
import re
from xml.etree import ElementTree as etree
from webob import Response as HttpResponse
from radarpost.mailbox import create_mailbox as _create_mailbox
from radarpost.mailbox import Message, MailboxInfo
from radarpost import plugins
from radarpost.plugins import plugin
from radarpost.feed import FeedSubscription, FEED_SUBSCRIPTION_TYPE
from radarpost.web.helpers import get_couchdb_server, get_database_name
from radarpost.web.helpers import get_mailbox, get_template, render
from radarpost.web.helpers import TemplateContext

###############################################
#
# REST ops for mailboxes themselves
#
###############################################
def mailbox_rest(request, mailbox_slug):
    if request.method == 'GET' or request.method == 'HEAD':
        return mailbox_exists(request, mailbox_slug)
    if request.method == 'POST':
        return create_mailbox(request, mailbox_slug)
    elif request.method == 'DELETE': 
        return delete_mailbox(request, mailbox_slug)
    else: 
        # 405 Not Allowed
        res = HttpResponse(status=405)
        res.allow = ['GET', 'HEAD', 'POST', 'DELETE']
        return res

def mailbox_exists(request, mailbox_slug):
    """
    tests existence of a mailbox. 
    returns 200 if the mailbox exists, 404 if not.
    """
    mb = get_mailbox(mailbox_slug)
    if mb is None:
        return HttpResponse(status=404)
    return HttpResponse()

VALID_TITLE_PAT = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_ \+\=\-\?\.\,\'\`\"\!\@\#\$\%\^\&\*\(\)\]\[\<\>\}\{]{0,255}$')
def create_mailbox(request, mailbox_slug):
    """
    create a mailbox.  request.POST may contain 
    a json object with initial mailbox info.
    """
    try:
        info = None
        if request.body:
            try:
                info = {}
                raw_info = json.loads(request.body)
                title = raw_info.get('title')
                if title:
                    if VALID_TITLE_PAT.match(title) is None:
                        raise ValueError()
                    info['name'] = raw_info['title']
            except:
                return HttpResponse(status=400)
        
        dbname = get_database_name(mailbox_slug)
        mb = _create_mailbox(get_couchdb_server(), dbname)
        if info is not None and len(info) > 0:
            mbinfo = MailboxInfo.get(mb)
            for k, v in info.items():
                setattr(mbinfo, k, v)
            mbinfo.store(mb)

        return HttpResponse(status=201)
    except PreconditionFailed:
        return HttpResponse(status=409)

def delete_mailbox(request, mailbox_slug):
    """
    destroys a mailbox.
    """
    couchdb = get_couchdb_server()
    try:
        dbname = get_database_name(mailbox_slug)
        del couchdb[dbname]
        return HttpResponse()
    except ResourceNotFound:
        return HttpResponse(status=404)

##############################################
#
# Feed output 
#
###############################################

ATOM_RENDERER_PLUGIN = 'radarpost.web.radar_ui.atom_renderer'
"""
This slot represents plugins that can render a Message
into an Atom entry.  

Most types can be handled by just creating a template called 
radar/atom/entry/<message_type>.xml

Specifically, the slot is filled with callables that accept a Message 
and a Request, and produce a zero argument callable returning the text
of an atom entry representing the Message.  If the Message cannot be handled,
None should be returned. eg: 

@plugin(ATOM_RENDERER_PLUGIN)
def _render_empty(message, request):
    def render(): 
        return "<entry></entry>"
    return render
"""

DEFAULT_ATOM_ENTRIES = 25
MAX_ATOM_ENTRIES = 100
def atom_feed(request, mailbox_slug):
    """
    renders the mailbox as an atom feed
    """
    if request.method != 'GET':
        res = HttpResponse(status=405)
        res.allow = ['GET']
        return res
    
    mb = get_mailbox(mailbox_slug)
    if mb is None:
        return HttpResponse(status=404)

    # number of entries
    try:
        limit = min(int(request.GET.get('limit', DEFAULT_ATOM_ENTRIES)), 
                    MAX_ATOM_ENTRIES)
    except:
        return HttpResponse(status=400)

    params = {'limit': limit, 
              'include_docs': True,
              'reduce': False,
              'descending': True}

    # starting point in time
    if 'startkey' in request.GET:
        params['startkey'] = request.GET['startkey']

    entries = []
    for message in Message.view(mb, Message.by_timestamp, **params): 
        renderer = _get_atom_renderer(message, request)
        if renderer is not None:
            entries.append(renderer)

    info = MailboxInfo.get(mb)
    
    # absolute url for requested feed
    feed_url = request.url
    ctx = TemplateContext(request, 
          {'id': feed_url,
           'self_link': feed_url,
           'updated': datetime.utcnow(), # XXX
           'title': info.name or mailbox_slug,
           'entries': entries,
          })

    res = HttpResponse(content_type='application/atom+xml')
    res.charset = 'utf-8'
    res.unicode_body = render('radar/atom/atom.xml', ctx)
    return res


def _get_atom_renderer(message, request):
    for renderer in plugins.get(ATOM_RENDERER_PLUGIN):
        r = renderer(message, request)
        if r is not None:
            return r
    return None


@plugin(ATOM_RENDERER_PLUGIN)
def _render_from_type_template(message, request):
    template = _atom_type_template(message)
    if template is None:
        return None
    
    def render_entry():
        return template.render(TemplateContext(request, 
                               {'message': message}))
    return render_entry

def _atom_type_template(message, force_type=None):
    """
    renders an atom entry template
    in radar/atom/entry/ according to the message_type
    field of the message.
    """
    if force_type is None: 
        mtype =  message.message_type
    else: 
        mtype = force_type
    
    template_name = 'radar/atom/entry/%s.xml' % mtype
    return get_template(template_name)

#################################################
#
# OPML based REST API for feed subscriptions
#
#################################################

def feeds_opml(request, mailbox_slug):
    """
    handles managing feed subscriptions using an OPML 
    document.
    """
    mb = get_mailbox(mailbox_slug)
    if mb is None:
        return HttpResponse(status=404)

    if request.method == 'GET':
        return HttpResponse(_get_opml(mb, request),
                            status=200,
                            content_type="text/x-opml")

    elif request.method == 'POST':
        return _post_opml(mb, request)

    elif request.method == 'PUT':
        return _put_opml(mb, request)

    else:
        res = HttpResponse(status=405)
        res.allow = ['GET', 'PUT', 'POST']
        return res


def _get_opml(mb, request):
    """
    build OPML doc from feed type subscriptions in the
    mailbox.
    """
    info = MailboxInfo.get(mb)

    root = etree.Element("opml", version="1.0")
    head = etree.Element("head")
    root.append(head)
    
    title = etree.Element("title")
    title.text = info.name or mb.name
    head.append(title)
    
    body = etree.Element("body")
    root.append(body)
    
    for sub in FeedSubscription.view(mb, FeedSubscription.by_type,
                                     startkey=FEED_SUBSCRIPTION_TYPE,
                                     endkey=FEED_SUBSCRIPTION_TYPE,
                                     include_docs=True):
        attrs = {
            'id': sub.id,
            'xmlUrl': sub['url'],
            'type': 'rss',
            'title': sub.get('title', sub['url'])
        }
        body.append(etree.Element("outline", **attrs))

    return etree.tostring(root)

def _post_opml(mb, request):
    """
    add a FeedSubscription for any new 
    feeds in the opml document given.
    """
    try:
        feeds = _feeds_in_opml(request.body)
    except: 
        return HttpResponse(status=400)
    
    new_urls = set(feeds.keys())
    for r in mb.view(FeedSubscription.by_url, keys=list(new_urls)):
        new_urls.remove(r.key)

    new_subs = []
    for url in new_urls:
        title = feeds[url] or url
        sub = FeedSubscription(url=url, title=title)
        new_subs.append(sub)

    imported = 0
    errors = []
    for r in mb.update(new_subs):
        if r[0] == True: 
            imported += 1
        else:
            errors.append(r)

    r = {"imported": imported, 
         "deleted": 0,
         "errors": len(errors)
         }
    return HttpResponse(json.dumps(r), content_type="application/json")

def _put_opml(mb, request):
    """
    Replace the set of feed subscriptions with 
    those specified in the opml document given.
    """
    try:
        feeds = _feeds_in_opml(request.body)
    except: 
        return HttpResponse(status=400)

    new_urls = set(feeds.keys())
    delete_docs = set()

    updates = []

    for r in mb.view(FeedSubscription.by_url):
        url = r.key
        if not url in feeds:
            delete_docs.add(r.id)
            updates.append({'_id': r.id,
                            '_rev': r.value['_rev'],
                            '_deleted': True})
        else:
            new_urls.remove(url)

    for url in new_urls:
        title = feeds[url] or url
        sub = FeedSubscription(url=url, title=title)
        updates.append(sub)

    imported = 0
    deleted = 0
    errors = []
    for vr in mb.update(updates):
        if vr[0] == True:
            if vr[1] in delete_docs:
                deleted += 1
            else:
                imported += 1
        else:
            errors.append(vr)

    r = {"imported": imported, 
         "deleted": deleted,
         "errors": len(errors)
         }
    return HttpResponse(json.dumps(r), content_type="application/json")

def _feeds_in_opml(opml):
    opml = etree.XML(opml)
    feeds = {}
    #for node in opml.xpath('//outline[@type="rss"]'):
    for node in opml.getiterator('outline'):
        if node.get('type', '').lower() == 'rss':
            url= node.get('xmlUrl', None)
            if url is not None:
                feeds[url] = node.get('title', '')
    return feeds