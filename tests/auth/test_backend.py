from django.core.cache import cache
from django.test import TestCase

from entree.enauth.models import Identity

from nose.tools import assert_raises, assert_equals

from entree.enauth.backends import AuthBackend


class TestBackend(TestCase):

    def setUp(self):
        super(TestBackend, self).setUp()
        cache.clear()

        self.username = 'foo@bar.cz'
        self.password = 'foo'
        self.user = Identity.objects.create(email=self.username, password=self.password, is_active=True)

        self.ab = AuthBackend()

    def test_authenticate_inactive_fail(self):
        user = Identity.objects.create(email='egg@foo.bar', password='foo', is_active=False)
        assert_equals(None, self.ab.authenticate(user.email, user.password))

    def test_authenticate_success(self):
        assert_equals(self.user, self.ab.authenticate(self.username, self.password))

    def test_authenticate_bad_password_fail(self):
        assert_equals(None, self.ab.authenticate(self.username, 'not %s' % self.password))

    def test_authenticate_bad_username_fail(self):
        assert_equals(None, self.ab.authenticate('not %s' % self.username, self.password))

    def test_get_user_success(self):
        assert_equals(self.user, self.ab.get_user(self.user.pk))

    def test_get_user_fail(self):
        assert_equals(None, self.ab.get_user(self.user.pk+1))
