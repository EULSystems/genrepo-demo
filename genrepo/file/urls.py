from django.conf.urls.defaults import *

urlpatterns = patterns('genrepo.file.views',
    url(r'^ingest/$', 'ingest_form', name='ingest'),
    url(r'^(?P<pid>[^/]+)/$', 'view_metadata', name='view'),
    url(r'^(?P<pid>[^/]+)/edit/$', 'edit_metadata', name='edit'),
    url(r'^(?P<pid>[^/]+)/master/$', 'download_file', name='download'),
)
