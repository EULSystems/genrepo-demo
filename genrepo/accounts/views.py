from django.shortcuts import render_to_response
from django.template import RequestContext
from genrepo.util import render_to_response

def index(request):
    return render_to_response('site_index.html', request=request)
    
