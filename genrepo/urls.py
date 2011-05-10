from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin

# auto discover models that should be available for db admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^genrepo/', include('genrepo.foo.urls')),
    # site index
    url(r'^$', 'genrepo.accounts.views.index', name="site-index"),

    # login/logout
    url(r'^accounts/', include('genrepo.accounts.urls', namespace='accounts')),
    # collections
    url(r'^collections/', include('genrepo.collection.urls', namespace='collection')),
    # files
    url(r'^files/', include('genrepo.file.urls', namespace='file')),

    # enable django db-admin
    (r'^db-admin/', include(admin.site.urls)),
)


# serve out media in django runserver for development
# DISABLE THIS IN PRODUCTION
if settings.DEV_ENV:
    import os
    # if there's not a genlib_media dir/link in the media directory, then
    # look for it in the virtualenv themes.
    if not os.path.exists(os.path.join(settings.MEDIA_ROOT, 'genlib_media')) and \
            'VIRTUAL_ENV' in os.environ:
        genlib_media_root = os.path.join(os.environ['VIRTUAL_ENV'],
                                         'themes', 'genlib', 'genlib_media')
        urlpatterns += patterns('',
            (r'^static/genlib_media/(?P<path>.*)$', 'django.views.static.serve', {
                'document_root': genlib_media_root,
                }),
        )

    urlpatterns += patterns('',
        (r'^static/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
            }),
    )

