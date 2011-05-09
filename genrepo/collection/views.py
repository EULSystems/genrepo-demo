from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.urlresolvers import reverse
from django.http import Http404
from django.template import RequestContext

from eulcore.django.fedora.server import Repository
from eulcore.fedora.models import DigitalObjectSaveFailure
from eulcore.django.auth.decorators import permission_required_with_403
from eulcore.django.http import HttpResponseSeeOtherRedirect
from eulcore.fedora.util import RequestFailed, PermissionDenied

from genrepo.collection.forms import CollectionDCEditForm
from genrepo.collection.models import CollectionObject
from genrepo.util import render_to_response, accessible

@permission_required_with_403('collection.add_collection')
def create_collection(request):
    '''Create a new :class:`~genrepo.collection.models.CollectionObject`.
    
    On GET, displays the form. On POST, creates a collection if the
    form is valid.
    '''
    return _create_or_edit_collection(request)

@permission_required_with_403('collection.change_collection')
def edit_collection(request, pid):
    '''Edit an existing
    :class:`~genrepo.collection.models.CollectionObject` identified by
    pid.

    On GET, displays the edit form.  On POST, updates the collection
    if the form is valid.
    '''
    return _create_or_edit_collection(request, pid)

def _create_or_edit_collection(request, pid=None):
    """View to create a new
    :class:`~genrepo.collection.models.CollectionObject` or update an
    existing one.

    On GET, display the form.  When valid form data is POSTed, creates
    a new collection (if pid is None) or updates an existing
    collection.
    """
    status_code = None
    repo = Repository(request=request)
    # get the object (if pid is not None), or create a new instance
    obj = repo.get_object(pid, type=CollectionObject)
   
    # on GET, instantiate the form with existing object data (if any)
    if request.method == 'GET':
        form = CollectionDCEditForm(instance=obj.dc.content)

    # on POST, create a new collection object, update DC from form
    # data (if valid), and save
    elif request.method == 'POST':
        form = CollectionDCEditForm(request.POST, instance=obj.dc.content)
        if form.is_valid():
            form.update_instance()
            # also use dc:title as object label
            obj.label = obj.dc.content.title
            try:
                if obj.exists:
                    action = 'updated'
                else:
                    action = 'created new'

                # save message must be specified in order for Fedora
                # to generate & store an ingest audit trail event
                result = obj.save('ingest via genrepo')
                messages.success(request,
            		'Successfully %s collection <a href="%s"><b>%s</b></a>' % \
                         (action, reverse('collection:edit', args=[obj.pid]), obj.pid))

		# maybe redirect to collection view page when we have one
                # - and maybe return a 201 Created status code
                return HttpResponseSeeOtherRedirect(reverse('site-index'))
            except (DigitalObjectSaveFailure, RequestFailed) as rf:
                # do we need a different error message for DigitalObjectSaveFailure?
                if isinstance(rf, PermissionDenied):
                    msg = 'You don\'t have permission to create a collection in the repository.'
                else:
                    msg = 'There was an error communicating with the repository.'
                messages.error(request,
                               msg + ' Please contact a site administrator.')

                # pass the fedora error code back in the http response
                status_code = getattr(rf, 'code', None)

    # if form is not valid, fall through and re-render the form with errors
    response = render_to_response('collection/edit.html',
            {'form': form, 'obj': obj}, request=request)
    # if a non-standard status code is set, set it in the response before returning
    if status_code is not None:
        response.status_code = status_code
    return response

def view_collection(request, pid):
    '''view an existing
    :class:`~genrepo.collection.models.CollectionObject` identified by
    pid.
    '''
    repo = Repository(request=request)
    obj = repo.get_object(pid, type=CollectionObject)
    # if the object does not exist or the current user doesn't have
    # permission to see that it exists, 404
    if not obj.exists:
        raise Http404
    return render_to_response('collection/view.html',
            {'obj': obj}, request=request)

def list_collections(request):
    '''list all collections in repository returns list of
    :class:`~genrepo.collection.models.CollectionObject`
    '''
    colls = CollectionObject.all()
    colls = list(accessible(colls))
    colls.sort(key=lambda coll: coll.label.upper()) # sort based on label

    return render_to_response('collection/list.html',
            {'colls': colls}, request=request)
