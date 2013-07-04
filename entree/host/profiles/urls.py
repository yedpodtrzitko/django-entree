from django.conf.urls import patterns, url

from entree.host.profiles.views import ProfileEdit

urlpatterns = patterns(
    'entree.host.views', # prefix
    url(r'^edit/(?P<site_id>\d+)/(?P<next_url>[\w\d=]+)/$', ProfileEdit.as_view(), name='profile_edit'),
    url(r'^edit/(?P<site_id>\d+)/$', ProfileEdit.as_view(), name='profile_edit'),

    #used only to generate appropriate link in class ShowApiView
    url(r'^edit/$', ProfileEdit.as_view(), name='profile_edit'),
)
