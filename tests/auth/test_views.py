import simplejson as json

from base64 import b64encode
from mock import Mock, patch
from nose.tools import assert_raises, assert_equals
from urlparse import urlparse
from datetime import timedelta, datetime

from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.cache import SessionStore
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.http import HttpRequest, HttpResponse, Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.test import TestCase
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.messages.storage.base import  BaseStorage

from entree.enauth.models import Identity, LoginToken, AUTH_TOKEN, MAIL_TOKEN, RESET_TOKEN
from entree.enauth.views import (EntreeAuthMixin, LoginView, LogoutView,
    LoginHashView, CreateIdentityView, IdentityVerifyView, IdentityVerifyResend,
    RecoveryLoginView, PasswordRecoveryRequestView, PasswordResetView, PasswordChangeView,
    ShowApiView)
from entree.common.utils import ENTREE_SAFE, calc_checksum, SHORT_CHECK
from entree.host.models import EntreeSite, SiteProfile


ENTREE = settings.ENTREE


def init_request():
    request = HttpRequest()
    request.method = 'GET'
    request.session = SessionStore()
    request.session.create()
    request._messages = BaseStorage(request)
    request.entree_user = AnonymousUser()

    return request


class TestAuthMixin(TestCase):

    def setUp(self):
        super(TestAuthMixin, self).setUp()
        cache.clear()

        self.user = Identity.objects.create(email='foo@bar.cz')

        self.request = init_request()

        self.mixin = EntreeAuthMixin()
        self.mixin.request = self.request


    def test_auth_mixin_login_set_all_the_shit_into_session(self):
        self.mixin.entree_login(self.user)

        assert ENTREE['SESSION_KEY'] in self.request.session
        assert ENTREE['STORAGE_TOKEN_KEY'] in self.request.session

    def test_auth_mixin_login_create_login_token(self):
        self.mixin.entree_login(self.user)

        token_str = self.request.session[ENTREE['STORAGE_TOKEN_KEY']]

        token = LoginToken.objects.get(value=token_str, user=self.user)

        assert_equals(AUTH_TOKEN, token.token_type)

    def test_login_flush_sess_if_another_user_lives_in_there(self):
        mock_flush = Mock()
        alien = Identity.objects.create(email='baz@bar.cz')

        self.request.session[ENTREE['SESSION_KEY']] = alien.pk
        self.request.session[SESSION_KEY] = 'foo'
        self.request.session.flush = mock_flush

        self.mixin.entree_login(self.user)

        assert_equals(True, mock_flush.called)

    def test_logout_set_anon_user_into_entree_user_prop(self):

        self.mixin.entree_logout()

        assert_equals(self.request.entree_user.__class__, AnonymousUser)

    def test_logout_sess_propss_are_deleted(self):

        self.request.session[ENTREE['SESSION_KEY']] = 'foo'
        self.request.session[ENTREE['STORAGE_TOKEN_KEY']] = 'bar'

        self.mixin.entree_logout()

        assert ENTREE['SESSION_KEY'] not in self.request.session
        assert ENTREE['STORAGE_TOKEN_KEY'] not in self.request.session

    @patch('entree.enauth.views.render_to_response')
    def test_next_url_overriden_by_inactive_profile(self, patched_render):

        site = EntreeSite.objects.create(pk=ENTREE['SITE_ID'])

        self.mixin.entree_login(self.user, site_id=site.pk)

        args, kwargs = patched_render.call_args
        template, context = args

        assert_equals(context['next_url'], reverse('profile_edit', kwargs={'site_id': site.pk}))

    @patch('entree.enauth.views.render_to_response')
    def test_next_url_overriden_queue_next_url(self, patched_render):

        site = EntreeSite.objects.create(pk=ENTREE['SITE_ID'])

        url = '/foo/'
        next_url = b64encode("%s:%s" % (url, calc_checksum(url, length=SHORT_CHECK) ) )

        self.mixin.entree_login(self.user, site_id=site.pk, next_url=next_url)

        args, kwargs = patched_render.call_args
        template, context = args

        assert_equals(context['next_url'], reverse('profile_edit', kwargs={'site_id': site.pk, 'next_url': next_url}))

    @patch('entree.enauth.views.render_to_response')
    def test_next_url_active_profile_passed(self, patched_render):

        site = EntreeSite.objects.create(pk=ENTREE['SITE_ID'])

        profile = SiteProfile.objects.create(user=self.user, site=site, is_active=True)

        url = '/foo/'
        next_url = b64encode("%s:%s" % (url, calc_checksum(url, length=SHORT_CHECK) ) )

        self.mixin.entree_login(self.user, site_id=site.pk, next_url=next_url)

        args, kwargs = patched_render.call_args
        template, context = args

        assert_equals(context['next_url'], url)


    @patch('entree.enauth.views.render_to_response')
    def test_token_available_in_context(self, patched_render):

        self.mixin.entree_login(self.user)

        args, kwargs = patched_render.call_args
        template, context = args

        token = LoginToken.objects.get(token_type=AUTH_TOKEN, user=self.user)
        assert_equals(context['user_token'], token.value)




class TestLoginLogoutViews(TestCase):

    def setUp(self):
        super(TestLoginLogoutViews, self).setUp()
        cache.clear()

        self.user_password = 'foo'
        self.user = Identity.objects.create(email='foo@bar.cz', password=self.user_password, is_active=True)

        self.request = init_request()
        self.request.entree_user = self.user

        self.valid_site = EntreeSite.objects.create(id=ENTREE['SITE_ID'], title='foo', is_active=True, secret=ENTREE['SECRET_KEY'], url="http://foobar.cz")


    def test_authed_user_redirected_to_profile(self):

        ViewClass = LoginView.as_view()
        response = ViewClass(self.request, origin_site=self.valid_site.pk)

        assert_equals(response.status_code, 302)
        assert_equals(response['Location'], reverse('profile_edit', kwargs={'site_id': self.valid_site.pk}))


    def test_no_origin_site_redirects_to_default(self):

        ViewClass = LoginView.as_view()
        response = ViewClass(self.request)

        assert_equals(response.status_code, 302)
        assert_equals(response['Location'], reverse('login', kwargs={'origin_site': ENTREE['DEFAULT_SITE']}))


    def test_anon_user_got_form_view(self):

        self.request.entree_user = AnonymousUser()

        ViewClass = LoginView.as_view()

        response = ViewClass(self.request, origin_site=self.valid_site.pk)

        assert_equals(response.status_code, 200)
        assert_equals(response.__class__, TemplateResponse)


    def test_login_via_form_valid(self):
        data = {
            'username': self.user.email,
            'password': self.user_password,
        }

        self.request.entree_user = AnonymousUser()
        self.request.method = 'POST'
        self.request.POST = data
        self.request.session = SessionStore()

        ViewClass = csrf_exempt(LoginView.as_view())
        ViewClass(self.request, origin_site=self.valid_site.pk)

        assert_equals(self.request.entree_user, self.user)

    def test_logout_form_valid(self):

        data = {
            'origin_site': self.valid_site.pk,
            'next_url': '/',
        }

        self.request.method = 'POST'
        self.request.POST = data
        self.request.session = SessionStore()

        ViewClass = csrf_exempt(LogoutView.as_view())
        ViewClass(self.request, site_id=self.valid_site.pk)

        assert_equals(self.request.entree_user.__class__, AnonymousUser)


    def test_view_loginhash(self):
        self.invalid_site = EntreeSite.objects.create(title='xfoo', is_active=False, secret='neco', url="http://vanyli.net")

        def mocked_render(context, **response_kwargs):
            assert_equals(context['domains_whitelist'], [urlparse(self.valid_site.url).hostname])
            assert_equals(context['entree'], ENTREE_SAFE)
            return HttpResponse()

        view = LoginHashView()
        view.render_to_response = mocked_render
        view.get(self.request)

    def test_view_loginhash_no_valid_url(self):
        self.valid_site.delete()
        def mocked_render(context, **response_kwargs):

            assert_equals(context['domains_whitelist'], [])

            return HttpResponse()

        view = LoginHashView()
        view.render_to_response = mocked_render
        view.get(self.request)


class TestPasswordViews(TestCase):

    def setUp(self):
        super(TestPasswordViews, self).setUp()
        cache.clear()

        self.user_password = 'foo'
        self.user = Identity.objects.create(email='foo@bar.cz', password=self.user_password)
        self.request = init_request()

    @patch('entree.enauth.mailer.send_mail')
    def test_recovery_valid_mail_redirected_to_finish_step(self, mocked_send):
        mocked_send.return_value = True

        data = {
            'email': self.user.email,
        }

        self.request.method = 'POST'
        self.request.POST = data

        ViewClass = csrf_exempt(PasswordRecoveryRequestView.as_view())
        response = ViewClass(self.request)
        assert_equals(response['Location'], reverse('recovery_finish'))

    @patch('entree.enauth.mailer.send_mail')
    def test_recovery_send_mail_fails_and_show_form_again(self, mocked_send):
        mocked_send.side_effect = Exception('x')

        data = {
            'email': self.user.email,
        }

        self.request.method = 'POST'
        self.request.POST = data

        ViewClass = csrf_exempt(PasswordRecoveryRequestView.as_view())
        response = ViewClass(self.request)

        assert_equals(response.status_code, 200)
        assert_equals(response.context_data['form'].is_valid(), False)

    def test_password_recovery_with_token_in_url_login_user(self):
        token = self.user.create_token(token_type=RESET_TOKEN)

        ViewClass = PasswordResetView.as_view()
        ViewClass(self.request, token=token.value, email=b64encode(self.user.email))

    def test_password_recovery_with_invalid_token_in_url_do_nothing(self):
        token = self.user.create_token(token_type=RESET_TOKEN)

        ViewClass = PasswordResetView.as_view()
        res = ViewClass(self.request, token='NOT%s' % token.value, email=b64encode(self.user.email))

        assert_equals(res['Location'], reverse('password_recovery'))


    def test_password_reset_post_valid(self):
        token = self.user.create_token(token_type=RESET_TOKEN)
        new_pwd  = 'newpwd'
        data = {
            'password': new_pwd,
            'password2': new_pwd,
        }

        self.request.method = 'POST'
        self.request.POST = data

        ViewClass = csrf_exempt(PasswordResetView.as_view())
        ViewClass(self.request, token=token.value, email=b64encode(self.user.email))

        updated_user = Identity.objects.get(pk=self.user.pk)

        assert_equals(updated_user.check_password(new_pwd), True)
        assert_raises(LoginToken.DoesNotExist, lambda: LoginToken.objects.get(pk=token.pk))

    def test_password_change_anonymous_redirected_away(self):
        ViewClass = PasswordChangeView.as_view()
        res = ViewClass(self.request)
        assert_equals(res['Location'], reverse('login'))

    def test_password_change_form_valid_change_password(self):

        new_pwd = '%s_neasi' % self.user_password
        data = {
            'old_password': self.user_password,
            'password': new_pwd,
            'password2': new_pwd,
        }

        self.request.method = 'POST'
        self.request.POST = data

        #create session
        auth = LoginView()
        auth.request = self.request
        auth.entree_login(self.user)

        ViewClass = csrf_exempt(PasswordChangeView.as_view())
        ViewClass(self.request)

        assert_equals(True, self.user.check_password(new_pwd))


class TestIdentityViews(TestCase):


    def setUp(self):
        super(TestIdentityViews, self).setUp()
        cache.clear()

        self.email = 'foo@bar.cz'
        self.password = 'heslo'

        self.request = init_request()

        self.user = Identity.objects.create(email='another@bar.cz', is_active=False, mail_verified=False)

        self.valid_site = EntreeSite.objects.create(id=ENTREE['SITE_ID'], title='foo', is_active=True, secret=ENTREE['SECRET_KEY'], url="http://foobar.cz")


    def test_form_valid_creates_identity_and_login(self):
        data = {
            'email': self.email,
            'password': self.password,
            'password2': self.password,
        }

        self.request.method = 'POST'
        self.request.POST = data

        ViewClass = csrf_exempt(CreateIdentityView.as_view())
        ViewClass(self.request, origin_site=self.valid_site.pk)

        identity = Identity.objects.get(email=self.email)

        assert_equals(identity, self.request.entree_user)
        assert_equals(False, identity.mail_verified)

    def test_create_without_site_id_raises_404(self):
        ViewClass = CreateIdentityView.as_view()
        assert_raises(Http404, lambda: ViewClass(self.request))

    def test_create_with_site_id_pass(self):
        ViewClass = CreateIdentityView.as_view()
        res = ViewClass(self.request, origin_site=self.valid_site.pk)
        assert_equals(type(res), TemplateResponse)

    @patch('entree.enauth.mailer.send_mail')
    def test_form_valid_send_activation_mail(self, mocked_send):
        mocked_send.return_value = True

        data = {
            'email': self.email,
            'password': self.password,
            'password2': self.password,
        }

        self.request.method = 'POST'
        self.request.POST = data

        ViewClass = csrf_exempt(CreateIdentityView.as_view())
        ViewClass(self.request, origin_site=self.valid_site.pk)

        assert_equals(True, mocked_send.called)
        assert LoginToken.objects.get(user=self.request.entree_user, token_type=MAIL_TOKEN)

    def test_verify_idenitity_while_anonymous_activate_user_and_delete_token(self):
        token = self.user.create_token(token_type=MAIL_TOKEN)
        verify_mail = b64encode(self.user.email)

        ViewClass = IdentityVerifyView.as_view()
        ViewClass(self.request, token=token.value, email=verify_mail)

        updated_user = Identity.objects.get(pk=self.user.pk)

        assert_equals(True, updated_user.is_active)
        assert_equals(True, updated_user.mail_verified)
        assert_raises(LoginToken.DoesNotExist, lambda: LoginToken.objects.get(token_type=MAIL_TOKEN, value=token.value))

    def test_verify_identity_invalid_token_only_show_instruction_template(self):

        verify_mail = b64encode(self.user.email)
        ViewClass = IdentityVerifyView.as_view()
        ViewClass(self.request, token='foobar', email=verify_mail)

        updated_user = Identity.objects.get(pk=self.user.pk)

        assert_equals(False, updated_user.is_active)
        assert_equals(False, updated_user.mail_verified)


    def test_verify_identity_mismatch_token_type_fail(self):
        token = LoginToken.objects.create(token_type=AUTH_TOKEN, value='foobarbaz', user=self.user)

        verify_mail = b64encode(self.user.email)
        ViewClass = IdentityVerifyView.as_view()
        ViewClass(self.request, token=token.value, email=verify_mail)

        updated_user = Identity.objects.get(pk=self.user.pk)

        assert_equals(False, updated_user.is_active)
        assert_equals(False, updated_user.mail_verified)

    def test_verify_identity_no_token_fallback_to_template_render(self):

        verify_mail = b64encode(self.user.email)
        ViewClass = IdentityVerifyView.as_view()
        res = ViewClass(self.request, token="", email=verify_mail)

        updated_user = Identity.objects.get(pk=self.user.pk)

        assert_equals(False, updated_user.is_active)
        assert_equals(False, updated_user.mail_verified)

        assert_equals(type(res), TemplateResponse)

    def test_verify_identity_rollback_on_login_fail(self):
        #TODO - find out how to mock IdentityVerifyView.entree_login
        class MockedIdentityVerifyView(IdentityVerifyView):
            def entree_login(self, identity, site_id=None, next_url=''):
                raise Exception('x')

        token = self.user.create_token(token_type=MAIL_TOKEN)
        verify_mail = b64encode(self.user.email)

        ViewClass = MockedIdentityVerifyView.as_view()
        res = ViewClass(self.request, token=token.value, email=verify_mail)
        assert_equals(type(res), HttpResponseRedirect)

    @patch('entree.enauth.mailer.send_mail')
    def test_resend_activation_mail_before_cooldown(self, mocked_send):
        mocked_send.return_value = True

        self.request.entree_user = self.user
        token = self.user.create_token(token_type=MAIL_TOKEN)

        verify_mail = b64encode(self.user.email)

        ViewClass = IdentityVerifyResend.as_view()
        response = ViewClass(self.request, token=token.value, email=verify_mail)

        assert_equals(response['Location'], reverse('verify_identity'))

    @patch('entree.enauth.mailer.send_mail')
    def test_resend_activation_mail_on_demand(self, mocked_send):
        mocked_send.return_value = True

        self.request.entree_user = self.user
        token = self.user.create_token(token_type=MAIL_TOKEN)
        token.touched = datetime.now() - timedelta(days=1)
        token.save()

        verify_mail = b64encode(self.user.email)

        ViewClass = IdentityVerifyResend.as_view()
        response = ViewClass(self.request, token=token.value, email=verify_mail)

        assert_equals(True, mocked_send.called)
        assert_equals(response['Location'], reverse('verify_identity'))


    @patch('entree.enauth.mailer.send_mail')
    def test_resend_activation_mail_on_demand_ajax(self, mocked_send):

        self.request.is_ajax = lambda: True
        self.request.entree_user = self.user

        token = self.user.create_token(token_type=MAIL_TOKEN)
        token.touched = datetime.now() - timedelta(days=1)
        token.save()

        verify_mail = b64encode(self.user.email)

        ViewClass = IdentityVerifyResend.as_view()
        response = ViewClass(self.request, token=token.value, email=verify_mail)

        response = json.loads(response.content)

        assert_equals(dict(send_status=True), response)
        assert_equals(True, mocked_send.called)


    def test_recovery_login_works(self):
        token = self.user.create_token(token_type=AUTH_TOKEN)
        self.request.GET['token'] = token.value

        ViewClass = RecoveryLoginView.as_view()
        ViewClass(self.request)

        assert_equals(self.request.entree_user, self.user)

    def test_recovery_invalid_token_passed_to_template_to_delete(self):

        delete_token = 'FOOBAR'

        def mocked_render(context, **response_kwargs):
            assert_equals(context['input_token'], delete_token)
            return HttpResponse()

        self.request.GET['token'] = delete_token

        view = RecoveryLoginView()
        view.render_to_response = mocked_render
        view.get(self.request)

        assert_equals(self.request.entree_user, AnonymousUser())


class TestApiView(TestCase):

    def setUp(self):
        super(TestApiView, self).setUp()
        cache.clear()

        self.request = init_request()

    def test_view_pass(self):
        ViewClass = ShowApiView.as_view()
        res = ViewClass(self.request)
        assert_equals(type(res), TemplateResponse)

    def test_view_site_pass(self):

        site = EntreeSite.objects.create(pk=ENTREE['SITE_ID'])

        ViewClass = ShowApiView.as_view()
        res = ViewClass(self.request, site_id=site.pk)
        assert_equals(type(res), TemplateResponse)
