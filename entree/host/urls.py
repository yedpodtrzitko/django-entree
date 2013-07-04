from django.conf.urls import patterns, url
from django.views.decorators.csrf import csrf_exempt

from entree.host.views import ProfileView, ProfileFetchView


urlpatterns = patterns('entree.host.views',
    url(r'^fetch/$', csrf_exempt(ProfileFetchView.as_view()), name='profile_fetch'),
    url(r'^$', ProfileView.as_view(), name='profile')
)
