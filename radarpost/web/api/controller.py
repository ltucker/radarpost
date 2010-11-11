import copy
from couchdb import ResourceConflict
from couchdb import ResourceNotFound, PreconditionFailed
from datetime import datetime
import json
import re
from xml.etree import ElementTree as etree
from webob import Response as HttpResponse
from radarpost.mailbox import create_mailbox as _create_mailbox, is_mailbox
from radarpost.mailbox import Message, MESSAGE_TYPE, MailboxInfo
from radarpost.mailbox import Subscription, SUBSCRIPTION_TYPE
from radarpost import plugins
from radarpost.plugins import plugin
from radarpost.feed import FeedSubscription, FEED_SUBSCRIPTION_TYPE
from radarpost.user import User, ROLE_ADMIN
from radarpost.user import PERM_CREATE, PERM_READ, PERM_UPDATE, PERM_DELETE
from radarpost.user import PERM_CREATE_MAILBOX
from radarpost.web.context import TemplateContext, check_etag, get_mailbox_etag

################################################
#
# User Login / Logout etc. 
#
################################################

def login(request):
    """
    handles session login
    """
    try:
        params = _get_params_by_ct(request)
        username = params['username']
        password = params['password']
    except: 
        return HttpResponse(status=400)
        
    # attempt actual login...
    udb = request.context.get_users_database()
    user = User.get_by_username(udb, username)
        
    if user is None: 
        return HttpResponse(status=401)
    
    if not user.check_password(password):
        return HttpResponse(status=401)
        
    # password was good, record in session
    request.context.set_session_user(user)

    if 'next' in params:
        req = HttpResponse(status=304)
        req.location = params['next']
        return req
    else: 
        return HttpResponse()

def logout(request):
    """
    handles session logout
    """
    request.context.set_session_user(None)
    return HttpResponse()

def current_user_info(request):
    return _user_info(request, request.context.user)

def create_user(request):
    """
    handles creating a user with userame 
    specified as a part of the request parameters
    """
    return _create_user(request)

def user_rest(request, userid):
    """
    REST dispatch for user methods
    """
    if request.method == 'HEAD': 
        return _user_exists(request, userid)
    if request.method == 'GET': 
        return _user_info(request, userid)
    if request.method == 'POST': 
        return _update_user(request, userid)
    if request.method == 'PUT': 
        return _create_user(request, userid)
    if request.method == 'DELETE':
        return _delete_user(request, userid)
    else: 
        res = HttpResponse(status=405)
        res.allow = ['HEAD', 'GET', 'POST', 'GET', 'PUT', 'DELETE']
        return res

VALID_USERNAME = re.compile("^[a-zA-Z0-9_]{1,64}$")
def _create_user(request, username=None):
    """
    helper to create users 
    ie POST /user or PUT /user/<username>
    """
    if not request.context.user.has_perm(PERM_CREATE, User): 
        return HttpResponse(status=401)

    try:
        params = _get_params_by_ct(request)
        if username is None:
            username = params.get('username')

        # validate
        if not VALID_USERNAME.match(username):
            return HttpResponse('Invalid username', status=400, content_type="text/plain")

        if 'password' in params: 
            if (not 'password2' in params or 
                params['password2'] != params['password']): 
                return HttpResponse('Passwords did not match', status=400, content_type="text/plain")
    except:
        return HttpResponse('Error parsing parameters', status=400, content_type="text/plain")

    try:
        user = User(username=username)
        if 'password' in params:
            user.set_password(params['password'])
        user.store(request.context.get_users_database())
        return HttpResponse(status=201)
    except ResourceConflict:
        return HttpResponse(status=409)

def _user_info(request, user):
    """
    helper that handles retreiving user info
    ie GET /user/<userid> or GET /user
    """
    if isinstance(user, basestring):
        udb = request.context.get_users_database()
        user = User.get_by_username(udb, user)
        if user is None: 
            return HttpResponse(status=404)

    if user.is_anonymous():
        info = {'is_anonymous': True}
    else:
        info = {'is_anonymous': False,
                'userid': user.username,
                'name': user.get_public_id()}

    return HttpResponse(json.dumps(info),
                        content_type="application/json")

def _update_user(request, username):
    """
    updates user info 
    ie POST /user/<username>
    """
    udb = request.context.get_users_database()
    user = User.get_by_username(udb, username)
    if user is None: 
        return HttpResponse(status=404)

    if not request.context.user.has_perm(PERM_UPDATE, obj=user):
        return HttpResponse(status=401)

    try:
        params = _get_params_by_ct(request)

        if 'password' in params: 
            if (not 'password2' in params or 
                params['password2'] != params['password']): 
                return HttpResponse('Passwords did not match', status=400, content_type="text/plain")
            user.set_password(params['password'])
    except: 
        return HttpResponse(status=400)

    try: 
        user.store(udb)
        return HttpResponse(status=200)
    except ResourceConflict:
        return HttpResponse(status=409)


def _user_exists(request, username):
    """
    tests existance of user with the given username
    ie HEAD /user/<username>
    """
    udb = request.context.get_users_database()
    user = User.get_by_username(udb, username)
    if user is None or not user.type == 'user':
        return HttpResponse(status=404)
    else:
        return HttpResponse(status=200)

def _delete_user(request, username): 
    """
    deletes a user
    """    
    udb = request.context.get_users_database()
    user = User.get_by_username(udb, username)
    if user is None or not user.type == 'user' or not user.username == username:
        return HttpResponse(status=404)

    if not request.context.user.has_perm(PERM_DELETE, user):
        return HttpResponse(status=401)

    del udb[user.id]
    return HttpResponse(status=200)

###############################################
#
# REST ops for mailboxes 
#
###############################################
def mailbox_rest(request, mailbox_slug):
    if request.method == 'GET' or request.method == 'HEAD':
        return mailbox_exists(request, mailbox_slug)
    elif request.method == 'PUT':
        return create_mailbox(request, mailbox_slug)
    elif request.method == 'POST':
        return update_mailbox(request, mailbox_slug)
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
    ctx = request.context 
    mb = ctx.get_mailbox(mailbox_slug)
    if mb is None:
        return HttpResponse(status=404)
    
    etag = get_mailbox_etag(mb)
    cached = check_etag(request, etag)
    if cached is not None:
        return cached
    
    res = HttpResponse(content_type="text/html")
    res.headers['etag'] = etag
    return res

def create_mailbox(request, mailbox_slug):
    """
    create a mailbox.  request.POST may contain
    a json object with initial mailbox info.
    """
    if not request.context.user.has_perm(PERM_CREATE_MAILBOX):
        return HttpResponse(status=401)
    
    try:
        info = None
        if request.body:
            try:
                info = _mailbox_info_json(request)
            except:
                return HttpResponse(status=400)
        
        ctx = request.context
        dbname = ctx.get_database_name(mailbox_slug)
        mb = _create_mailbox(ctx.get_couchdb_server(), dbname)
        if info is not None and len(info) > 0:
            mbinfo = MailboxInfo.get(mb)
            for k, v in info.items():
                setattr(mbinfo, k, v)
            mbinfo.store(mb)

        return HttpResponse(status=201)
    except PreconditionFailed:
        return HttpResponse(status=409)

def update_mailbox(request, mailbox_slug):
    """
    updates a mailbox's info
    """
    ctx = request.context
    couchdb = ctx.get_couchdb_server()
    try:
        dbname = ctx.get_database_name(mailbox_slug)
        mb = couchdb[dbname]
        if not is_mailbox(mb):
            return HttpResponse(status=404)
        if not ctx.user.has_perm(PERM_UPDATE, mb):
            return HttpResponse(status=401)

        try:
            info = _mailbox_info_json(request)
        except: 
            return HttpResponse(status=400)

        mbinfo = MailboxInfo.get(mb)
        try:
            mbinfo.user_update(info)
        except: 
            return HttpResponse(status=400)
        mbinfo.store(mb)
        
        return HttpResponse()
    except ResourceNotFound:
        return HttpResponse(status=404)

VALID_TITLE_PAT = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_ \+\=\-\?\.\,\'\`\"\!\@\#\$\%\^\&\*\(\)\]\[\<\>\}\{]{0,255}$')
def _mailbox_info_json(request):
    info = {}
    raw_info = json.loads(request.body)
    title = raw_info.get('title')
    if title:
        if VALID_TITLE_PAT.match(title) is None:
            raise ValueError()
        info['title'] = raw_info['title']
    return info

def delete_mailbox(request, mailbox_slug):
    """
    destroys a mailbox.
    """
    ctx = request.context
    couchdb = ctx.get_couchdb_server()
    try:
        dbname = ctx.get_database_name(mailbox_slug)
        mb = couchdb[dbname]
        if not is_mailbox(mb):
            return HttpResponse(status=404)
        if not ctx.user.has_perm(PERM_DELETE, mb):
            return HttpResponse(status=401)
        del couchdb[dbname]
        return HttpResponse()
    except ResourceNotFound:
        return HttpResponse(status=404)

##############################################
#
# Feed output 
#
###############################################

ATOM_RENDERER_PLUGIN = 'radarpost.web.api.atom_renderer'
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
def atom_feed_latest(request, mailbox_slug):
    """
    renders the mailbox as an atom feed
    """
    ctx = request.context
    mb = ctx.get_mailbox(mailbox_slug)
    if mb is None:
        return HttpResponse(status=404)

    if not ctx.user.has_perm(PERM_READ, mb):
        return HttpResponse(status=401)

    etag = get_mailbox_etag(mb)
    cached = check_etag(request, etag)
    if cached is not None: 
        return cached

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

    latest_messages = Message.view(mb, Message.by_timestamp, **params) 
    return _render_atom_feed(request, mb, latest_messages)

def _render_atom_feed(request, mb, messages):    
    entries = []
    for message in messages:
        renderer = _get_atom_renderer(message, request)
        if renderer is not None:
            entries.append(renderer)

    info = MailboxInfo.get(mb)
    
    # absolute url for requested feed
    feed_url = request.url
    template_info = TemplateContext(request,
          {'id': feed_url,
           'self_link': feed_url,
           'updated': datetime.utcnow(), # XXX
           'title': info.title or request.context.get_mailbox_slug(mb.name),
           'entries': entries,
          })

    res = HttpResponse(content_type='application/atom+xml')
    res.charset = 'utf-8'
    res.unicode_body = request.context.render('radar/atom/atom.xml', template_info)
    res.headers['etag'] = get_mailbox_etag(mb)
    
    return res


def _get_atom_renderer(message, request):
    for renderer in plugins.get(ATOM_RENDERER_PLUGIN):
        r = renderer(message, request)
        if r is not None:
            return r
    return None


@plugin(ATOM_RENDERER_PLUGIN)
def _render_from_type_template(message, request):
    template = _atom_type_template(message, request)
    if template is None:
        return None
    
    def render_entry():
        return template.render(TemplateContext(request, 
                               {'message': message}))
    return render_entry

def _atom_type_template(message, request, force_type=None):
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
    return request.context.get_template(template_name)

#################################################
#
# JSON API for subscription management
#
#################################################

def subscriptions_rest(request, mailbox_slug):
    if request.method == 'GET': 
        return _get_subscriptions_json(request, mailbox_slug)
    elif request.method == 'POST': 
        return _create_subscriptions_json(request, mailbox_slug)

def _get_subscriptions_json(request, mailbox_slug):

    ctx = request.context
    mb = ctx.get_mailbox(mailbox_slug)
    if mb is None:
        return HttpResponse(status=404)

    subs = []
    for sub in Subscription.view(mb, Subscription.by_type,
                                 include_docs=True):
        subs.append(_sub_json(sub))

    return HttpResponse(json.dumps(subs),
                        content_type="application/json")

def _create_subscriptions_json(request, mailbox_slug):
    ctx = request.context
    mb = ctx.get_mailbox(mailbox_slug)
    if mb is None:
        return HttpResponse(status=404)

    if not ctx.user.has_perm(PERM_UPDATE, mb):
        return HttpResponse(status=401)

    try:
        params = json.loads(request.body)
    except:
        return HttpResponse(status=400)

    if not isinstance(params, dict):
        return HttpResponse(status=400)

    try:
        sub_type = params.get('type')
        del params['type']
        
        sub = Subscription.create_type(sub_type)
        sub.user_update(params)
        sub.store(mb)
        return HttpResponse(json.dumps({'slug': sub.id}),
                            content_type='application/json',
                            status=201)
    except: 
        return HttpResponse(status=400)


def subscription_rest(request, mailbox_slug, sub_slug):
    if request.method == 'HEAD': 
        return _subscription_exists(request, mailbox_slug, sub_slug) 
    elif request.method == 'GET':
        return _get_subscription_json(request, mailbox_slug, sub_slug)
    elif request.method == 'POST': 
        return _update_subscription(request, mailbox_slug, sub_slug)
    elif request.method == 'DELETE': 
        return _delete_subscription(request, mailbox_slug, sub_slug)

def _subscription_exists(request, mailbox_slug, sub_slug):
    ctx = request.context
    mb = ctx.get_mailbox(mailbox_slug)
    if mb is None:
        return HttpResponse(status=404)
    sub = Subscription.load(mb, sub_slug)
    if sub is None or sub.type != SUBSCRIPTION_TYPE: 
        return HttpResponse(status=404)
    return HttpResponse()

        
def _get_subscription_json(request, mailbox_slug, sub_slug):
    ctx = request.context
    mb = ctx.get_mailbox(mailbox_slug)
    if mb is None:
        return HttpResponse(status=404)

    sub = Subscription.load(mb, sub_slug)
    if sub is None or sub.type != SUBSCRIPTION_TYPE: 
        return HttpResponse(status=404)

    return HttpResponse(json.dumps(_sub_json(sub)), 
                        content_type="application/json")

def _update_subscription(request, mailbox_slug, sub_slug):
    ctx = request.context
    mb = ctx.get_mailbox(mailbox_slug)
    if mb is None:
        return HttpResponse(status=404)

    sub = Subscription.load(mb, sub_slug)
    if sub is None or sub.type != SUBSCRIPTION_TYPE: 
        return HttpResponse(status=404)

    if not ctx.user.has_perm(PERM_UPDATE, mb):
        return HttpResponse(status=401)


    params = _get_params_by_ct(request)
    try:
        sub.user_update(params)
        sub.store(mb)
        return HttpResponse()
    except:
        return HttpResponse(status=400)
    
def _delete_subscription(request, mailbox_slug, sub_slug):
    ctx = request.context
    mb = ctx.get_mailbox(mailbox_slug)
    if mb is None:
        return HttpResponse(status=404)

    if not ctx.user.has_perm(PERM_UPDATE, mb):
        return HttpResponse(status=401)

    sub = Subscription.load(mb, sub_slug)
    if sub is None or sub.type != SUBSCRIPTION_TYPE: 
        return HttpResponse(status=404)

    try:
        del mb[sub.id]
    except ResourceNotFound: 
        return HttpResponse(status=404)

    return HttpResponse()

def _sub_json(sub):
    sub_dict = copy.deepcopy(sub.unwrap())
    
    sub_dict['slug'] = sub_dict['_id']
    del sub_dict['_id']
    
    sub_dict['type'] = sub_dict['subscription_type']
    del sub_dict['subscription_type']
    
    return sub_dict

#################################################
#
# OPML based REST API for feed subscriptions
#
#################################################

def subscriptions_opml(request, mailbox_slug):
    """
    handles managing feed subscriptions using an OPML 
    document.
    """
    ctx = request.context
    mb = ctx.get_mailbox(mailbox_slug)
    if mb is None:
        return HttpResponse(status=404)

    if request.method == 'GET':
        return HttpResponse(_get_opml(request, mb),
                            status=200,
                            content_type="text/x-opml")

    elif request.method == 'POST':
        return _post_opml(request, mb)

    elif request.method == 'PUT':
        return _put_opml(request, mb)

    else:
        res = HttpResponse(status=405)
        res.allow = ['GET', 'PUT', 'POST']
        return res


def _get_opml(request, mb):
    """
    build OPML doc from feed type subscriptions in the
    mailbox.
    """
    info = MailboxInfo.get(mb)

    root = etree.Element("opml", version="1.0")
    head = etree.Element("head")
    root.append(head)
    
    title = etree.Element("title")
    title.text = info.title or mb.name
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

def _post_opml(request, mb):
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

def _put_opml(request, mb):
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
    
###############
    
def message_rest(request, mailbox_slug, message_slug):
    if request.method == 'DELETE': 
        return _delete_message(request, mailbox_slug, message_slug)
        
def _delete_message(request, mailbox_slug, message_slug):
    ctx = request.context
    mb = ctx.get_mailbox(mailbox_slug)
    if mb is None:
        return HttpResponse(status=404)

    if not ctx.user.has_perm(PERM_UPDATE, mb):
        return HttpResponse(status=401)

    message = Message.load(mb, message_slug)
    if message is None or message.type != MESSAGE_TYPE: 
        return HttpResponse(status=404)

    try:
        del mb[message.id]
    except ResourceNotFound: 
        return HttpResponse(status=404)

    return HttpResponse()

###############
# helpers

def _get_params_by_ct(request):
    """
    get the request parameters based on the content type specified in the 
    request.  supports form encoding and json. returns a dict or None 
    if there was no recognized parameters.
    """
    content_type = request.headers.get('Content-Type', '').split(';')[0]

    if content_type == 'application/x-www-form-urlencoded': 
        return request.params
    elif content_type == 'application/json':
        return json.loads(request.body)
    else:
        return None



