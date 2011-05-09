import django.shortcuts
from django.template import RequestContext
from eulcore.fedora.util import RequestFailed

def render_to_response(template, dictionary=None, request=None, mimetype=None):
    context = RequestContext(request) if request else None
    return django.shortcuts.render_to_response(template, dictionary,
            context, mimetype)


def accessible(olist):
    '''Iterate through an input object list, and yield only those that exist
    and don't throw Fedora exceptions.'''
    for obj in olist:
        try:
            if obj.exists:
                yield obj
        except RequestFailed:
            pass
