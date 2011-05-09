import django.shortcuts
from django.template import RequestContext
from eulcore.fedora.util import RequestFailed

def render_to_response(*args, **kwargs):
    if 'request' in kwargs:
        kwargs['context_instance'] = RequestContext(kwargs.pop('request'))
    return django.shortcuts.render_to_response(*args, **kwargs)


def accessible(olist):
    '''Iterate through an input object list, and yield only those that exist
    and don't throw Fedora exceptions.'''
    for obj in olist:
        try:
            if obj.exists:
                yield obj
        except RequestFailed:
            pass
