from django.core.cache import cache
from django.http import HttpRequest
from django.test import TestCase

from entree.enauth.forms import EntreeAuthForm, CreateIdentityForm, RecoveryForm, BasicPasswordForm, ChangePasswordForm
from entree.enauth.models import Identity
from entree.host.models import EntreeSite

from mock import Mock, patch
from nose.tools import assert_raises, assert_equals


class TestIdentifyForms(TestCase):

    def setUp(self):
        super(TestIdentifyForms, self).setUp()
        cache.clear()

        self.username = 'foo@bar.cz'
        self.password = 'foo'
        self.user = Identity.objects.create(email=self.username, password=self.password, is_active=True)


    def test_auth_form_clean(self):
        data = {'username': self.username, 'password': self.password}
        form = EntreeAuthForm(data=data)

        assert_equals(True, form.is_valid())
        assert_equals(self.username, str(form.cleaned_data['username']))
        assert_equals(self.password, str(form.cleaned_data['password']))

    def test_auth_form_bad_password(self):
        data = {'username': self.username, 'password': 'not %s' % self.password}

        form = EntreeAuthForm(data=data)
        form.is_valid()

        #TODO - better assert
        assert_equals(['__all__'], form.errors.keys())


    '''
    def test_auth_form_inactive_user(self):
        password = 'foo'
        user = Identity.objects.create(email='foo@bar.baz', password=password)

        form = EntreeAuthForm(data=dict(username=user.email, password=password))
        form.is_valid()

        #TODO - better assert
        assert_equals(['__all__'], form.errors.keys())
    '''

    def test_missing_session_middleware_raises(self):
        mck = Mock()
        mck.return_value = False

        request = HttpRequest()
        request.session = Mock()
        request.session.test_cookie_worked = lambda: False

        form = EntreeAuthForm(request=request, data=dict(username=self.username, password=self.password))
        form.is_valid()

        #TODO - better assert
        assert_equals(['__all__'], form.errors.keys())

    def test_get_user_id_returns_id(self):

        form = EntreeAuthForm(data=dict(username=self.username, password=self.password))
        form.is_valid()

        assert_equals(self.user.pk, form.get_user_id())

    def test_get_user_returns_user(self):

        form = EntreeAuthForm(data=dict(username=self.username, password=self.password))
        form.is_valid()

        assert_equals(self.user, form.get_user())

    def test_get_user_returns_none_if_auth_failed(self):

        form = EntreeAuthForm(data=dict(username=self.username, password='not %s' % self.password))
        form.is_valid()

        assert_equals(None, form.get_user())



class TestCreateIdentityForm(TestCase):

    def setUp(self):
        super(TestCreateIdentityForm, self).setUp()
        cache.clear()

        self.username = 'foo@bar.cz'
        self.password = 'foo'

    def test_create_idenity_pass(self):

        data = {
            'password': self.password,
            'password2': self.password,
            'email': self.username,
        }

        form = CreateIdentityForm(data=data)
        assert_equals(True, form.is_valid())

    def test_create_colliding_identity_fail(self):
        data = {
            'password': self.password,
            'password2': self.password,
            'email': self.username,
        }

        form = CreateIdentityForm(data=data)
        assert_equals(True, form.is_valid())
        form.save()

        form2 = CreateIdentityForm(data=data)
        assert_equals(False, form2.is_valid())

    def test_mismatch_passwords_failed(self):
        data = {
            'password': self.password,
            'password2': "not %s" % self.password,
            'email': self.username,
        }

        form = CreateIdentityForm(data=data)

        assert_equals(False, form.is_valid())
        assert_equals(['password2'], form.errors.keys())


class TestPasswordForms(TestCase):

    def setUp(self):
        super(TestPasswordForms, self).setUp()
        cache.clear()

        self.username = 'foo@bar.cz'
        self.password = 'foo'
        self.user = Identity.objects.create(email=self.username, password=self.password, is_active=True)


    def test_recovery_unknown_email_form_invalid(self):

        form = RecoveryForm(data=dict(email='not%s' % self.user.email))
        assert_equals(False, form.is_valid())


    def test_recovery_form_valid(self):

        form = RecoveryForm(data=dict(email=self.user.email))
        assert_equals(True, form.is_valid())

    @patch('entree.enauth.mailer.send_mail')
    def test_send_mail_fail_form_invalid(self, mocked_send):
        mocked_send.side_effect = Exception('x')
        form = RecoveryForm(data=dict(email=self.user.email))
        assert_equals(False, form.is_valid())

    def test_password_form_diff_passwords_raises(self):
        pwd = 'foo'
        form = BasicPasswordForm(data=dict(password=pwd, password2='not%s' % pwd))
        assert_equals(False, form.is_valid())

    def test_change_password_invalid_old_pwd_raises(self):
        data = {
            'old_password': 'not%s' % self.password,
            'password': 'new%s' % self.password,
            'password2': 'new%s' % self.password
            }
        form = ChangePasswordForm(data=data, entree_user=self.user)
        assert_equals(False, form.is_valid())
        assert_equals(['old_password'], form.errors.keys())
