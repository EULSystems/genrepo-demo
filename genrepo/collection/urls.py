from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('genrepo.collection.views',
    url(r'^new/$', 'create', name='new'),
    url(r'^(?P<pid>[^/]+)/edit/$', 'edit', name='edit'),
    url(r'^(?P<pid>[^/]+)/view/$', 'view', name='view'),
)

