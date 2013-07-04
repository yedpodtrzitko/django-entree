from django.conf.urls.defaults import url, patterns
from entree.user.views import LoginView, EditView, LogoutView, RegisterView

urlpatterns = patterns('',
    url(r'^logout/(?P<return_url>.*)$', LogoutView.as_view(), name='logout'),
    url(r'^register/(?P<return_url>.*)$', RegisterView.as_view(), name='registration'),
    url(r'^edit/(?P<return_url>.*)$', EditView.as_view(), name='edit_profile'),
    url(r'^login/(?P<return_url>.*)$', LoginView.as_view(), name='login')
)
