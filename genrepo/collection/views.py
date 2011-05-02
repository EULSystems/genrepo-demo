from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template import RequestContext

from eulcore.django.fedora.server import Repository
from eulcore.django.http import HttpResponseSeeOtherRedirect
from eulcore.fedora.util import RequestFailed, PermissionDenied

from genrepo.collection.forms import CollectionDCEditForm
from genrepo.collection.models import CollectionObject

def create(request):
    """View to create a new
    :class:`~genrepo.collection.models.CollectionObject`.

    On GET, display the form.
    On POST, create a new Collection if the form is valid.
    """
    status_code = None
    
    # on GET, instantiate a new form with no data
    if request.method == 'GET':
        form = CollectionDCEditForm()

    # on POST, create a new collection object, update DC from form
    # data (if valid), and save
    elif request.method == 'POST':
        repo = Repository()
        obj = repo.get_object(type=CollectionObject)
        form = CollectionDCEditForm(request.POST, instance=obj.dc.content)
        if form.is_valid():
            form.update_instance()
            # also use dc:title as object label
            obj.label = obj.dc.content.title
            try:
                result = obj.save()
                messages.success(request,
            		'Successfully created new collection <b>%s</b>' % obj.pid)
#            	'Successfully created new collection <a href="%s">%s</a>' % \
#                 (reverse('collections:edit', args=[obj.pid]), obj.pid))

		# maybe redirect to collection view page when we have one
                # - and maybe return a 201 Created status code
                return HttpResponseSeeOtherRedirect(reverse('site-index'))
            except RequestFailed as rf:
                if isinstance(rf, PermissionDenied):
                    msg = 'You don\'t have permission to create a collection in the repository.'
                else:
                    msg = 'There was an error communicating with the repository.'
                messages.error(request,
                               msg + ' Please contact a site administrator.')

                # pass the fedora error code back in the http response
                status_code = rf.code

    # if form is not valid, fall through and re-render the form with errors
    response = render_to_response('collection/edit.html', {'form': form},
            context_instance=RequestContext(request))
    # if a non-standard status code is set, set it in the response before returning
    if status_code is not None:
        response.status_code = status_code
    return response

