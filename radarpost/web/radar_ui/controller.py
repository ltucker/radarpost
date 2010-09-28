from webob import Response as HttpResponse
from radarpost.mailbox import MailboxInfo
from radarpost.web.context import TemplateContext, render_to_response

def login(request):
    next_page = request.params.get('next', request.context.url_for('front_page'))
    ctx = {'next': next_page}
    return render_to_response('radar/login.html', 
                              TemplateContext(request, ctx))

def logout(request):
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
        slug = ctx.get_mailbox_slug(mb.name)
        info = MailboxInfo.get(mb)
        mailboxes.append({
            'slug': slug,
            'title': info.name or slug
        })
    return render_to_response('radar/list_mailboxes.html', 
                              TemplateContext(request, {'mailboxes': mailboxes}))
        
    
def create_mailbox(request):
    if request.method != 'GET':
        res = HttpResponse(status=405)
        res.allow = ['GET']
        return res
    return render_to_response('radar/create_mailbox.html', 
                              TemplateContext(request, {}))
    
def view_mailbox(request, mailbox_slug):
    return render_to_response('radar/view_mailbox.html', 
                              TemplateContext(request, {}))
