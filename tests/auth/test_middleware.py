from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.http import HttpRequest
from django.test import TestCase
from django.conf import settings

from entree.enauth.middleware import get_user, AuthMiddleware
from entree.enauth.models import Identity

from nose.tools import assert_raises, assert_equals, assert_not_equals


class TestAuthMiddleware(TestCase):

    def setUp(self):
        super(TestAuthMiddleware, self).setUp()
        cache.clear()

        self.user = Identity.objects.create(email='foo@bar.cz')

        self.request = HttpRequest()
        self.request.session = SessionStore()
        self.request.session[settings.ENTREE['SESSION_KEY']] = self.user.pk


    def test_get_user_via_sess_key(self):
        obtained_user = get_user(self.request)

        assert_equals(obtained_user, self.user)

    def test_get_user_no_sess_key(self):
        self.request.session = SessionStore()
        obtained_user = get_user(self.request)

        assert_equals(AnonymousUser, obtained_user.__class__)

    def test_process_request_get_user_set_into_request(self):
        AuthMiddleware().process_request(self.request)

        assert_equals(self.request.entree_user, self.user)

    def test_redirect_if_not_verified(self):

        res = AuthMiddleware().process_request(self.request)
        assert_equals(res['Location'], reverse('verify_identity'))

    def test_pass_if_fully_verified(self):

        self.user.is_active = True
        self.user.mail_verified = True
        self.user.save()

        res = AuthMiddleware().process_request(self.request)
        assert_equals(None, res)


    def test_pass_if_user_wanna_logout(self):

        self.request.path = reverse('logout')

        res = AuthMiddleware().process_request(self.request)
        assert_equals(None, res)
