from cache_tools.utils import get_cached_object
from django.test import TestCase
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import IntegrityError

from entree.enauth.models import LoginToken, Identity, MAIL_TOKEN
from nose.tools import assert_raises, assert_equals


class TestAuthManagers(TestCase):

    def setUp(self):
        super(TestAuthManagers, self).setUp()

    def reset_tokens(self):
        LoginToken.objects.all().delete()
        Identity.objects.all().delete()

    def test_token_manager_raises_if_not_exists(self):
        self.reset_tokens()

        assert_raises(ObjectDoesNotExist, lambda: get_cached_object(LoginToken, value='foobar'))

    def test_token_manager_cache_fallback_to_db(self):
        self.reset_tokens()

        token_user = Identity.objects.create()
        save_token = LoginToken.objects.create(value='FOO', user=token_user)

        get_token = get_cached_object(LoginToken, value='FOO')
        assert_equals(save_token, get_token)

    def test_token_manager_different_token_type_get_success(self):
        self.reset_tokens()

        token_user = Identity.objects.create()
        save_token = LoginToken.objects.create(value='TEST2', user=token_user, token_type=MAIL_TOKEN)

        assert_equals(save_token, get_cached_object(LoginToken, value='TEST2'))

    def test_two_same_tokens_collide(self):
        self.reset_tokens()

        token_user = Identity.objects.create()

        LoginToken.objects.create(value='COLLIDE_ME', user=token_user)

        assert_raises(IntegrityError, lambda: LoginToken.objects.create(value='COLLIDE_ME', user=token_user))
