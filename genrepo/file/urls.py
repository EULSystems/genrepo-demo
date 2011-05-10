from django.conf.urls.defaults import *

urlpatterns = patterns('genrepo.file.views',
    url(r'^ingest/$', 'ingest_form', name='ingest'),
)
