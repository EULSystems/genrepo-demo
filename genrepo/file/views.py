from django.contrib import messages
from django.core.urlresolvers import reverse
from rdflib import URIRef

from eulcore.django.fedora.server import Repository
from eulcore.django.http import HttpResponseSeeOtherRedirect
from eulcore.fedora.rdfns import relsext

from genrepo.file.forms import IngestForm
from genrepo.file.models import FileObject
from genrepo.util import render_to_response

def ingest_form(request):
    """Display or process the file ingest form. On GET, display the form. On
    valid POST, reposit the submitted file in a new digital object.
    """
    if request.method == 'POST':
        form = IngestForm(request.POST, request.FILES)
        if form.is_valid():
            repo = Repository(request=request)
            fobj = repo.get_object(type=FileObject)
            st = (fobj.uriref, relsext.isMemberOfCollection, 
                  URIRef(form.cleaned_data['collection']))
            fobj.rels_ext.content.add(st)
            fobj.master.content = request.FILES['file']
            fobj.save('ingesting user content')

            messages.success(request, 'Successfully ingested <b>%s</b>' % (fobj.pid,))
            return HttpResponseSeeOtherRedirect(reverse('site-index'))
    else:
        form = IngestForm()
    return render_to_response('file/ingest.html', 
        {'form': form}, request=request)
