from django.conf.urls.defaults import patterns, url
from django.core.urlresolvers import reverse


urlpatterns = patterns('django.contrib.auth.views',
    url(r'^login/$', 'login',
        {'template_name': 'accounts/login.html'}, name='login'),
    url(r'^logout/$', 'logout',
        {'next_page': reverse('site-index')}, name='logout'),
)

