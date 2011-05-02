from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('genrepo.collection.views',
    url(r'^new/$', 'create_or_edit', name='new'),
    url(r'^(?P<pid>[^/]+)/edit/$', 'create_or_edit', name='edit'),
)

