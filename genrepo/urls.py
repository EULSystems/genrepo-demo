from django.conf.urls.defaults import *
from django.contrib import admin

# auto discover models that should be available for db admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^genrepo/', include('genrepo.foo.urls')),

    # enable django db-admin
    (r'^db-admin/', include(admin.site.urls)),
)
