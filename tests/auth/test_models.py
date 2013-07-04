from cache_tools.utils import get_cached_object
from django.contrib.auth.hashers import UNUSABLE_PASSWORD
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import IntegrityError
from django.test import TestCase

from entree.enauth.models import Identity, MAIL_TOKEN, LoginToken
from nose.tools import assert_raises, assert_equals, assert_not_equals, assert_almost_equals
from mock import patch, Mock, call


class TestIdentity(TestCase):

    def setUp(self):
        super(TestIdentity, self).setUp()
        cache.clear()

        self.user = Identity.objects.create(email='foo@bar.cz')

    def tearDown(self):
        super(TestIdentity, self).tearDown()
        LoginToken.objects.all().delete()
        Identity.objects.all().delete()

    def test_strip_email(self):
        assert_equals('good@example.com', Identity.objects.create(email='GOOD@examplE.com ').email)

    def test_create_with_existing_email_raised(self):
        ident = Identity(email=self.user.email)
        assert_raises(IntegrityError, ident.save)

    def test_create_with_existing_anycase_username_raised(self):
        ident = Identity(email=self.user.email)
        assert_raises(IntegrityError, ident.save)

    def test_create_token(self):
        token = self.user.create_token()

        assert_equals(token.__class__.__name__, 'LoginToken')

    def test_create_mail_token(self):
        token = self.user.create_token(token_type=MAIL_TOKEN)
        assert_equals(token.token_type, MAIL_TOKEN)

    def test_identity_check_password(self):
        self.user.set_password('foo')

        assert_equals(True, self.user.check_password('foo'))
        assert_equals(False, self.user.check_password('food'))

    def test_indentity_update_password(self):
        ident = Identity(password='sha1$c6218$161d1ac8ab38979c5a31cbaba4a67378e7e60845')
        ident.save()
        ident.set_password = Mock()

        password_checked = ident.check_password('password')
        assert_equals(True, password_checked)
        assert_equals(1, ident.set_password.call_count)

    def test_user_has_unusable_password(self):
        assert_equals(self.user.password, UNUSABLE_PASSWORD)
        self.user.set_password("")
        assert_equals(self.user.password, UNUSABLE_PASSWORD)

    def test_delete_token_flush_cache(self):
        token_key = 'TOKEN_KEY'
        token = LoginToken.objects.create(user=self.user, value=token_key)
        get_cached_object(LoginToken, value=token_key)
        token.delete()
        assert_raises(ObjectDoesNotExist, lambda: get_cached_object(LoginToken, value=token_key))

    def test_create_invalid_token_type(self):
        assert_raises(ValueError, lambda: self.user.create_token(token_type='!FOO!'))

    def test_identity_returns_auth_status(self):
        assert_equals(True, self.user.is_authenticated())

    def test_get_identity_basic_data(self):
        assert_equals(dict(email=self.user.email), self.user.basic_data)
