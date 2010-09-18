from django import template
from django.utils.feedgenerator import rfc3339_date

register = template.Library()
register.filter('rfc3339', rfc3339_date)

class AtomEntryNode(template.Node):
    def __init__(self, renderer_id):
        self.renderer_id = renderer_id

    def render(self, context):
        renderer = context.get(self.renderer_id)
        return renderer(context)

def do_atom_entry(parser, token):
    try:
        tag_name, renderer_id = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires a single argument" % token.contents.split()[0]
    return AtomEntryNode(renderer_id)
register.tag('atom_entry', do_atom_entry)
