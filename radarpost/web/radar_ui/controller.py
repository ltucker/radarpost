from operator import attrgetter
from urllib import quote_plus
from webob import Response as HttpResponse
from radarpost.mailbox import MailboxInfo, Subscription, Message, MailboxInfo
from radarpost.user import PERM_CREATE, PERM_READ, PERM_UPDATE, PERM_DELETE
from radarpost.user import PERM_CREATE_MAILBOX
from radarpost.web.context import TemplateContext, render_to_response
from radarpost import plugins
from radarpost.plugins import plugin

######################################
#
# view helpers
#
######################################

def handle_unauth(request):
    if request.context.user.is_anonymous():
        # redirect to login with any additional info
        login_url = request.context.url_for('login', next=request.url)
        login_url = request.relative_url(login_url)
        res = HttpResponse(status=301)
        res.location = login_url
        return res
    else: 
        # logged in, but current user does not have permission
        # show message indicating unauthorized.
        return render_to_response('radar/unauthorized.html',
                                  TemplateContext(request, {}))

def unauth_handler(request, *args, **kw):
    return HttpResponse(status=401)

def login_required(controller_action):
    def wrapped_action(request, *args, **kw):
        if request.context.user is None or request.context.user.is_anonymous():
            return unauth_handler(request, *args, **kw)
        else:
            return controller_action(*args, **kw)
    wrapped_action.__name__ = controller_action.__name__
    return wrapped_action

#####################################
#
# views
#
######################################

def login(request):
    ctx = {}
    next_page = request.params.get('next')
    if next_page:
        ctx = {'next': next_page}
    return render_to_response('radar/login.html', 
                              TemplateContext(request, ctx))

def logout(request):
    request.context.set_session_user(None)
    return render_to_response('radar/logout.html', TemplateContext(request, {}))

def signup(request):
    if request.method == 'GET':
        return render_to_response('radar/signup.html', TemplateContext(request, {}))
        
def front_page(request):
    return render_to_response('radar/front_page.html', 
                              TemplateContext(request, {}))

def list_mailboxes(request):
    ctx = request.context
    mailboxes = []
    for mb in ctx.iter_mailboxes():
        if not ctx.user.has_perm(PERM_READ, mb): 
            continue

        slug = ctx.get_mailbox_slug(mb.name)
        info = MailboxInfo.get(mb)
        mailboxes.append({
            'slug': slug,
            'title': info.title or 'Untitled',
            'db': mb
        })
    return render_to_response('radar/list_mailboxes.html', 
                              TemplateContext(request, {'mailboxes': mailboxes}))

    
def create_mailbox(request):
    if request.method != 'GET':
        res = HttpResponse(status=405)
        res.allow = ['GET']
        return res
    
    ctx = request.context
    if not ctx.user.has_perm(PERM_CREATE_MAILBOX):
        return handle_unauth(request)
        
    return render_to_response('radar/create_mailbox.html', 
                              TemplateContext(request, {}))

def view_mailbox_latest(request, mailbox_slug):
    ctx = request.context
    mb = ctx.get_mailbox(mailbox_slug)
    if mb is None:
        return HttpResponse(status=404)

    if not ctx.user.has_perm(PERM_READ, mb):
        return handle_unauth(request)

    start = request.GET.get('start', None)
    limit = 10
    params = {'limit': limit + 1, 
              'include_docs': True,
              'reduce': False,
              'descending': True}
    if start is not None:
        params['startkey'] = start

    messages = []
    next_key = None
    for i, row in enumerate(mb.view(Message.by_timestamp, **params)):
        if i == limit:
            next_key = row.key
        else:
            messages.append(Message.wrap(row.doc))

    if next_key:
        next_params = {'start': next_key}
    else:
        next_params = None
    
    return _render_messages(request, mb, messages, next_params=next_params)

def _render_messages(request, mailbox, messages, next_params=None):
    ctx = request.context
    entries = []
    for message in messages:
        renderer = _get_hatom_renderer(message, request)
        if renderer is not None:
            entries.append(renderer)

    info = MailboxInfo.get(mailbox)
    mailbox_slug = request.context.get_mailbox_slug(mailbox.name)
    
    ctx = {}
    ctx['mailbox'] = mailbox
    ctx['mailbox_slug'] = mailbox_slug
    ctx['mailbox_title'] = info.title or mailbox_slug
    ctx['entries'] = entries
    
    if next_params:
        q = dict(request.GET)
        q.update(next_params)
        qs = ''
        for k, v in q.items():
            qs += '&%s=%s' % (quote_plus(k), quote_plus(v))
        next_link = request.path + '?' + qs[1:]    
        
        ctx['next_link'] = next_link

    return render_to_response('radar/view_mailbox.html', 
                              TemplateContext(request, ctx))


HATOM_RENDERER_PLUGIN = 'radarpost.web.radar_ui.hatom_renderer'
def _get_hatom_renderer(message, request):
    for renderer in plugins.get(HATOM_RENDERER_PLUGIN):
        r = renderer(message, request)
        if r is not None:
            return r
    return None


@plugin(HATOM_RENDERER_PLUGIN)
def _render_hatom_from_type_template(message, request):
    template = _hatom_type_template(message, request)
    if template is None:
        return None
    
    def render_entry():
        return template.render(TemplateContext(request, 
                               {'message': message}))
    return render_entry

def _hatom_type_template(message, request, force_type=None):
    """
    renders an atom entry template
    in radar/hatom/entry/ according to the message_type
    field of the message.
    """
    if force_type is None: 
        mtype =  message.message_type
    else: 
        mtype = force_type
    
    template_name = 'radar/hatom/entry/%s.html' % mtype
    return request.context.get_template(template_name)


def manage_subscriptions(request, mailbox_slug):
    ctx = request.context
    mb = ctx.get_mailbox(mailbox_slug)
    if mb is None:
      return HttpResponse(status=404)

    if not ctx.user.has_perm(PERM_READ, mb):
      return handle_unauth(request)

    info = MailboxInfo.get(mb)

    subs = []
    for sub in Subscription.view(mb, Subscription.by_type,
                                 include_docs=True):
        subs.append(sub)

    ctx = {}
    ctx['mailbox'] = mb
    ctx['mailbox_slug'] = mailbox_slug
    ctx['mailbox_title'] = info.title or mailbox_slug
    ctx['subscriptions'] = sorted(subs, key=attrgetter('title'))

    return render_to_response('radar/subscriptions.html', 
                            TemplateContext(request, ctx))


def manage_info(request, mailbox_slug):
    ctx = request.context
    mb = ctx.get_mailbox(mailbox_slug)
    if mb is None:
      return HttpResponse(status=404)

    if not ctx.user.has_perm(PERM_EDIT, mb):
      return handle_unauth(request)

    ctx = {}
    ctx['mailbox'] = mb
    ctx['mailbox_slug'] = mailbox_slug
    return render_to_response('radar/edit.html', 
                            TemplateContext(request, ctx))
