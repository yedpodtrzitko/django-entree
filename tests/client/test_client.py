from urllib2 import HTTPError
from StringIO import StringIO
import pickle

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse
from django.test.testcases import TestCase
from django.conf import settings

from entree.user.managers import EntreeUserFetcherMixin
from entree.user.middleware import get_user, InvalidUser, InvalidAuth, AuthMiddleware
from entree.user.db.models import EntreeDBUser
from entree.common.utils import COOKIE_CHECKSUM_SEPARATOR, calc_checksum

from mock import patch, Mock
from nose.tools import assert_raises, assert_equals

ENTREE  = settings.ENTREE
ECOOKIE = ENTREE['COOKIE']


class DBUserTestCase(TestCase):

    UserClass = EntreeDBUser


class TestEntreeDBUser(DBUserTestCase):

    def setUp(self):
        super(TestEntreeDBUser, self).setUp()
        cache.clear()

        self.user = self.UserClass()

    def test_has_key_returns_key(self):
        key = 'foo'
        user = self.UserClass(key=key)
        assert_equals(key, user.key)

    def test_unicode_repr_user(self):
        user = self.UserClass(email='foo@bar.cz')
        assert_equals(True, 'foo@bar.cz' in unicode(user))

    def test_str_repr_user(self):
        user = self.UserClass(email='foo@bar.cz')
        print str(user)
        assert_equals(True, 'foo@bar.cz' in str(user))

    def test_save_user_caches_it(self):
        user = self.UserClass(key='foo', email='foo@bar.cz')
        user.save()

        cached = self.UserClass.objects.get(key='foo')
        assert_equals(cached, user)

    def test_user_is_anonymous_property(self):
        assert_equals(False, self.user.is_anonymous())

    def test_user_is_authenticated_property(self):
        assert_equals(True, self.user.is_authenticated())

    def test_user_get_delete_messages_property(self):
        assert_equals([], self.UserClass().get_and_delete_messages())

    def test_str_user_pass(self):
        user = self.UserClass(key='foo', email='foo@bar.cz')
        assert_equals(user.key, 'foo')
        assert_equals(True, 'foo@bar.cz' in  str(user))


class TestEntreeCacheUserManager(DBUserTestCase):
    def setUp(self):
        super(TestEntreeCacheUserManager, self).setUp()
        cache.clear()

    def test_get_unmatching_user_raises(self):
        self.UserClass.objects.create(key='foo', email='foo@bar.cz')
        assert_raises(ObjectDoesNotExist, lambda: self.UserClass.objects.get(key='bar'))

    def test_get_matching_user(self):
        user = self.UserClass.objects.create(key='foo', email='foo@bar.cz')
        db_user = self.UserClass.objects.get(key='foo')
        assert_equals(user, db_user)

    def test_save_user_without_email_raises(self):
        assert_raises(ValueError, lambda: self.UserClass.objects.create(key='bar'))


class TestEntreeUserFetcher(DBUserTestCase):

    def setUp(self):
        super(TestEntreeUserFetcher, self).setUp()
        cache.clear()
        self.fetcher = EntreeUserFetcherMixin()

    def test_bad_checksum_raises(self):
        cookie_val = 'w/ checksum value'
        invalid_cookie = COOKIE_CHECKSUM_SEPARATOR.join([cookie_val, calc_checksum(cookie_val, length=10)])[:-1]
        assert_raises(InvalidAuth, self.fetcher.fetch, invalid_cookie)

    def test_no_checksum_pass_and_perform_fetch(self):
        cookie_val = 'no_checksum_value'

        self.fetcher.perform_fetch = Mock()
        self.fetcher.perform_fetch.return_value = AnonymousUser()

        assert_equals(AnonymousUser(), self.fetcher.fetch(cookie_val))
        assert self.fetcher.perform_fetch.called

    @patch('entree.client.managers.urlopen')
    def test_perform_fetch_403_raises_invalid(self, mocked_urlopen):

        mocked_urlopen.side_effect = HTTPError(url='foo', code=403, msg='you shall not pass', hdrs=None, fp=None)
        cookie_val = 'no_checksum_value'

        assert_raises(InvalidAuth, self.fetcher.perform_fetch, cookie_val)

    @patch('entree.client.managers.urlopen')
    def test_perform_fetch_404_raises_anonymous(self, mocked_urlopen):

        mocked_urlopen.side_effect = HTTPError(url='foo', code=404, msg='you shall not pass', hdrs=None, fp=None)
        cookie_val = 'no_checksum_value'

        assert_equals(AnonymousUser, self.fetcher.perform_fetch(cookie_val).__class__)

    @patch('entree.client.managers.urlopen')
    def test_perform_fetch_returns_entreeuser(self, mocked_urlopen):

        if self.__class__.__name__ == 'TestEntreeUserFetcherCache':
            from nose.plugins.skip import SkipTest
            raise SkipTest("entree.client.db in installed_apps means bad import")

        mocked_urlopen.return_value = StringIO("""{"email": "foo@bar.cz"}""")
        cookie_val = 'no_checksum_value'

        ret = self.fetcher.perform_fetch(cookie_val)
        assert_equals(self.UserClass, ret.__class__)
        assert_equals('foo@bar.cz', ret.email)


    @patch('entree.client.managers.urlopen')
    def test_perform_fetch_invalid_response_ret_anonymous(self, mocked_urlopen):

        mocked_urlopen.return_value = StringIO("""{invalid_json "foo"}""")
        cookie_val = 'no_checksum_value'

        ret = self.fetcher.perform_fetch(cookie_val)
        assert_equals(AnonymousUser, ret.__class__)


class TestAuthMiddleware(DBUserTestCase):

    def setUp(self):
        super(TestAuthMiddleware, self).setUp()
        cache.clear()

        self.raw_request = HttpRequest()
        self.raw_request.COOKIES = {}
        self.raw_request.session = object()

        self.raw_response = HttpResponse()

        self.mi = AuthMiddleware()


    def test_get_user_no_cookie_user_is_anonymous(self):
        assert_equals(AnonymousUser, type(get_user(self.raw_request)))

    @patch('entree.client.managers.EntreeUserFetcherMixin.fetch')
    def test_get_user_invalid_cookie_deleted(self, mocked_fetch):

        mocked_fetch.side_effect = InvalidAuth('foo')

        r = self.raw_request
        r.COOKIES[ECOOKIE['NAME']] = 'foo'

        assert_equals(InvalidUser, type(get_user(r)))
        assert_equals({}, r.COOKIES)

    def test_process_request_inject_entree_user_property(self):
        self.mi.process_request(self.raw_request)

        assert_equals(AnonymousUser, self.raw_request.entree_user.__class__)

    def test_process_response_no_cookie_set_cookie(self):
        self.raw_request.entree_user = AnonymousUser()
        assert ECOOKIE['NAME'] not in self.raw_response.cookies.keys()
        self.mi.process_response(self.raw_request, self.raw_response)
        assert ECOOKIE['NAME'] in self.raw_response.cookies.keys()

    def test_process_response_anon_cookie_dont_set_cookie(self):
        self.raw_request.entree_user = AnonymousUser()
        self.raw_request.COOKIES[ECOOKIE['NAME']] = ECOOKIE['ANONYMOUS_VALUE']
        self.mi.process_response(self.raw_request, self.raw_response)

        assert_equals([], self.raw_response.cookies.keys())

    def test_process_response_invalid_cookie_dont_set_cookie(self):
        self.raw_request.entree_user = InvalidUser()
        self.raw_request.COOKIES[ECOOKIE['NAME']] = ECOOKIE['INVALID']
        self.mi.process_response(self.raw_request, self.raw_response)

        assert_equals([], self.raw_response.cookies.keys())

    def test_process_response_valid_cookie_checksum_calculation(self):
        self.raw_request.entree_user = AnonymousUser()

        cookie_val = 'no checksum value'
        self.raw_request.COOKIES[ECOOKIE['NAME']] = cookie_val
        self.mi.process_response(self.raw_request, self.raw_response)
        expected_cookie = COOKIE_CHECKSUM_SEPARATOR.join([cookie_val, calc_checksum(cookie_val, length=10)])
        set_cookie = self.raw_response.cookies[ ECOOKIE['NAME'] ]
        assert expected_cookie in str(set_cookie)

    def test_process_response_valid_cookie_valid_checksum_dont_set_cookie(self):
        #self.raw_request.entree_user = AnonymousUser()

        cookie_val = 'w/ checksum value'
        expected_cookie = COOKIE_CHECKSUM_SEPARATOR.join([cookie_val, calc_checksum(cookie_val, length=10)])

        self.raw_request.COOKIES[ECOOKIE['NAME']] = expected_cookie
        self.mi.process_response(self.raw_request, self.raw_response)

        assert_equals([], self.raw_response.cookies.keys())


    def test_process_response_cookie_invalid_checksum_set_cookie(self):
        #self.raw_request.entree_user = AnonymousUser()

        cookie_val = 'w/ checksum value'
        expected_cookie = COOKIE_CHECKSUM_SEPARATOR.join([cookie_val, calc_checksum(cookie_val, length=10)])

        self.raw_request.COOKIES[ECOOKIE['NAME']] = expected_cookie[:-1]
        self.mi.process_response(self.raw_request, self.raw_response)

        assert ECOOKIE['INVALID'] in  str( self.raw_response.cookies[ECOOKIE['NAME']] )
