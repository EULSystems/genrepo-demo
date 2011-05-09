from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('genrepo.collection.views',
    url(r'^$', 'list_collections', name='list'),
    url(r'^new/$', 'create_collection', name='new'),
    url(r'^(?P<pid>[^/]+)/edit/$', 'edit_collection', name='edit'),
    url(r'^(?P<pid>[^/]+)/$', 'view_collection', name='view'),
)

