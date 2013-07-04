from django.conf.urls import patterns, url
from entree.enauth.views import (
    CreateIdentityView, LoginView, IdentityVerifyView, LogoutView, LoginHashView,
    IdentityVerifyResend, RecoveryLoginView, PasswordResetView, PasswordRecoveryRequestView,
    FinishRecoveryView, PasswordChangeView, ShowApiView)

#TODO - cleanup
urlpatterns = patterns('entree.enauth.views',
    url(r'^api/show/(?P<site_id>\d+)/$', ShowApiView.as_view(), name='api_show'),
    url(r'^api/show/$', ShowApiView.as_view(), name='api_show'),
    url(r'^iframe-login/$', LoginHashView.as_view(), name='login_hash'),

    url(r'^login/recovery/(?P<origin_site>\d+)/$', RecoveryLoginView.as_view(), name='login-recovery'),

    url(r'^login/$', LoginView.as_view(), name='login'),  # dummy url
    url(r'^login/(?P<origin_site>\d+)/$', LoginView.as_view(), name='login'),
    url(r'^login/(?P<origin_site>\d+)/(?P<next_url>\S+)/$', LoginView.as_view(), name='login'),

    url(r'^logout/$', LogoutView.as_view(), name='logout'),  # dummy url
    url(r'^logout/(?P<origin_site>\d+)/$', LogoutView.as_view(), name='logout'),
    url(r'^logout/(?P<origin_site>\d+)/(?P<next_url>\S+)/$', LogoutView.as_view(), name='logout'),

    url(r'^register/$', CreateIdentityView.as_view(), name='register'),  # dummy url
    url(r'^register/(?P<origin_site>\d+)/$', CreateIdentityView.as_view(), name='register'),
    url(r'^register/(?P<origin_site>\d+)/(?P<next_url>\S+)/$', CreateIdentityView.as_view(), name='create_identity'),

    #each of these urls below should start w/ the same string
    #there's middleware which controls inactive account if: url.startswith(reverse('verify_identity'))
    url(r'^verify/$', IdentityVerifyView.as_view(), name='verify_identity'),
    url(r'^verify/(?P<email>[A-Za-z0-9=]+)/(?P<token>\w+)/$', IdentityVerifyView.as_view(), name='verify_identity'),

    url(r'^verify/resend/$', IdentityVerifyResend.as_view(), name='verify_resend'),
    # ^ each of these urls above should start w/ the same string

    url(r'^password-change/$', PasswordChangeView.as_view(), name='password_change'),
    url(r'^password-recovery/$', PasswordRecoveryRequestView.as_view(), name='password_recovery'),
    url(r'^password-recovery/finish/(?P<email>[A-Za-z0-9=]+)/(?P<token>\S+)/$', PasswordResetView.as_view(), name='recovery_finish'),
    url(r'^password-recovery/finish/$', FinishRecoveryView.as_view(), name='recovery_finish'),

    url(r'^$', LoginView.as_view(), name='homepage')
)
