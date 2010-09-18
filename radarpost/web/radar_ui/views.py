from django import forms
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseNotAllowed
from django.shortcuts import render_to_response
from django.template import RequestContext
from radarpost.mailbox import MAILBOXINFO_ID
from radarpost.web.helpers import get_mailbox_slug, iter_mailboxes
from radarpost.web.radar_api.views import mailbox_rest


def front_page(request):
    return render_to_response('radar/front_page.html', 
                              RequestContext(request, {}))

def list_mailboxes(request):
    
    mailboxes = []
    for mb in iter_mailboxes():
        slug = get_mailbox_slug(mb.name)
        info = mb[MAILBOXINFO_ID]
        mailboxes.append({
            'slug': slug,
            'title': info.get('name') or slug
        })
    return render_to_response('radar/list_mailboxes.html', 
                              RequestContext(request, {'mailboxes': mailboxes}))
        
    
def create_mailbox(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
    return render_to_response('radar/create_mailbox.html', 
                              RequestContext(request, {}))
    
def view_mailbox(request, mailbox_slug):
    if request.method != 'GET':
        return mailbox_rest(request, mailbox_slug)

    return render_to_response('radar/view_mailbox.html', 
                              RequestContext(request, {})) 

def always_404(request):
    return HttpResponseNotFound()