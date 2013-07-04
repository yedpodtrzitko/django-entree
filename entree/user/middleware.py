import logging

from django.conf import settings
from django.utils.functional import SimpleLazyObject
from django.contrib.auth.models import AnonymousUser
from entree.common.utils import COOKIE_CHECKSUM_SEPARATOR, calc_checksum


logger = logging.getLogger(__name__)
ENTREE = settings.ENTREE
ECOOKIE = ENTREE['COOKIE']
COOKIE_CHECKSUM_LENGTH = 10
CACHED_USER_PROPERTY = '_entree_cached_user'


class InvalidAuth(Exception):
    pass


class InvalidUser(AnonymousUser):
    pass


def get_user(request):
    def fetch_user(token):
        from entree.user.models import EntreeUser
        try:
            user = EntreeUser.objects.fetch(token)
        except InvalidAuth:
            logger.info('deleting cookie %s' % token)
            del request.COOKIES[ECOOKIE['NAME']]
            user = InvalidUser()
        return user

    if not hasattr(request, CACHED_USER_PROPERTY):
        token = request.COOKIES.get(ECOOKIE['NAME'], '')
        if token in ('', ECOOKIE['ANONYMOUS_VALUE']):
            user = AnonymousUser()
        else:
            user = fetch_user(token)
        setattr(request, CACHED_USER_PROPERTY, user)
    return getattr(request, CACHED_USER_PROPERTY)


class AuthMiddleware(object):
    def process_request(self, request):
        assert hasattr(request, 'session'), "The Django authentication middleware requires session middleware to be installed. Edit your MIDDLEWARE_CLASSES setting to insert 'django.contrib.sessions.middleware.SessionMiddleware'."
        request.__class__.entree_user = SimpleLazyObject(lambda: get_user(request))

    def process_response(self, request, response):
        #TODO - update comment
        """
        check if login cookie exists
        if not, set anonymous (readable by JS) and do nothing
        if anonymous cookie already set, do nothing
        if user cookie set, check is user is valid
        """
        try:
            token_cookie = request.COOKIES[ECOOKIE['NAME']]
        except KeyError:
            invalid = request.entree_user.__class__ is InvalidUser
            self._set_anonymous_cookie(response, invalid)
            return response

        if token_cookie in (ECOOKIE['ANONYMOUS_VALUE'], ECOOKIE['INVALID']):
            return response

        try:
            token, checksum = token_cookie.split(COOKIE_CHECKSUM_SEPARATOR)
        except ValueError:
            token = token_cookie
            checksum = calc_checksum(token, length=COOKIE_CHECKSUM_LENGTH)
            new_val = COOKIE_CHECKSUM_SEPARATOR.join((token, checksum))

            response.set_cookie(key=ECOOKIE['NAME'], value=new_val,
                                path=ECOOKIE['PATH'],
                                domain=ECOOKIE['DOMAIN'], httponly=True)

        else:
            expected_checksum = calc_checksum(token, length=COOKIE_CHECKSUM_LENGTH)
            if expected_checksum != checksum:
                if ECOOKIE['NAME'] in request.COOKIES:
                    del request.COOKIES[ECOOKIE['NAME']]
                self._set_anonymous_cookie(response, invalid=True)

        return response

    def _set_anonymous_cookie(self, response, invalid=False):
        """
        anonymous cookie cannot be httponly, has to be writable by JS
        """
        val = ECOOKIE['ANONYMOUS_VALUE'] if not invalid else ECOOKIE['INVALID']
        response.set_cookie(key=ECOOKIE['NAME'], value=val, path=ECOOKIE['PATH'], domain=ECOOKIE['DOMAIN'])
