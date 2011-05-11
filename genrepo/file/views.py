from django.contrib import messages
from django.core.urlresolvers import reverse
from rdflib import URIRef

from eulcore.django.auth.decorators import permission_required_with_403
from eulcore.django.fedora.server import Repository
from eulcore.django.http import HttpResponseSeeOtherRedirect
from eulcore.fedora.models import DigitalObjectSaveFailure
from eulcore.fedora.rdfns import relsext
from eulcore.fedora.util import RequestFailed, PermissionDenied

from genrepo.file.forms import IngestForm, DublinCoreEditForm
from genrepo.file.models import FileObject
from genrepo.util import render_to_response

@permission_required_with_403('file.add_file')
def ingest_form(request):
    """Display or process the file ingest form. On GET, display the form. On
    valid POST, reposit the submitted file in a new digital object.
    """
    if request.method == 'POST':
        form = IngestForm(request.POST, request.FILES)
        if form.is_valid():
            # TODO: set label/dc:title based on filename;
            # set file mimetype in dc:format
            # TODO: file checksum?
            repo = Repository(request=request)
            fobj = repo.get_object(type=FileObject)
            st = (fobj.uriref, relsext.isMemberOfCollection, 
                  URIRef(form.cleaned_data['collection']))
            fobj.rels_ext.content.add(st)
            fobj.master.content = request.FILES['file']
            # pre-populate the object label and dc:title with the uploaded filename
            fobj.label = fobj.dc.content.title = request.FILES['file'].name
            fobj.save('ingesting user content')

            messages.success(request, 'Successfully ingested <b>%s</b>' % (fobj.pid,))
            return HttpResponseSeeOtherRedirect(reverse('site-index'))
    else:
        initial_data = {}
        # if collection is specified in url parameters, pre-select the
        # requested collection on the form via initial data
        if 'collection' in request.GET:
            initial_data['collection'] = request.GET['collection']
        form = IngestForm(initial=initial_data)
    return render_to_response('file/ingest.html', 
        {'form': form}, request=request)

def edit_metadata(request, pid):
    """View to edit the metadata for an existing
    :class:`~genrepo.file.models.FileObject` .

    On GET, display the form.  When valid form data is POSTed, updates
    thes object.
    """
    status_code = None
    repo = Repository(request=request)
    # get the object (if pid is not None), or create a new instance
    obj = repo.get_object(pid, type=FileObject)
   
    # on GET, instantiate the form with existing object data (if any)
    if request.method == 'GET':
        form = DublinCoreEditForm(instance=obj.dc.content)

    # on POST, create a new collection object, update DC from form
    # data (if valid), and save
    elif request.method == 'POST':
        form = DublinCoreEditForm(request.POST, instance=obj.dc.content)
        if form.is_valid():
            form.update_instance()
            # also use dc:title as object label
            obj.label = obj.dc.content.title
            try:
                result = obj.save('updated metadata')
                messages.success(request,
            		'Successfully updated <a href="%s"><b>%s</b></a>' % \
                         (reverse('file:edit', args=[obj.pid]), obj.pid))

		# maybe redirect to file view page when we have one
                return HttpResponseSeeOtherRedirect(reverse('site-index'))
            except (DigitalObjectSaveFailure, RequestFailed) as rf:
                # do we need a different error message for DigitalObjectSaveFailure?
                if isinstance(rf, PermissionDenied):
                    msg = 'You don\'t have permission to modify this object in the repository.'
                else:
                    msg = 'There was an error communicating with the repository.'
                messages.error(request,
                               msg + ' Please contact a site administrator.')

                # pass the fedora error code back in the http response
                status_code = getattr(rf, 'code', None)

    # if form is not valid, fall through and re-render the form with errors
    response = render_to_response('file/edit.html',
            {'form': form, 'obj': obj}, request=request)
    # if a non-standard status code is set, set it in the response before returning
    if status_code is not None:
        response.status_code = status_code
    return response

