'''
from entree.client.cached.models import EntreeCacheUser
from tests.client.test_client import TestEntreeDBUser, TestEntreeCacheUserManager, TestEntreeUserFetcher, TestAuthMiddleware


class CacheUserTestCase(object):
    UserClass = EntreeCacheUser


class TestEntreeCacheUser(CacheUserTestCase, TestEntreeDBUser):
    pass


class TestEntreeCacheUserManagerCache(CacheUserTestCase, TestEntreeCacheUserManager):
    pass

class TestEntreeUserFetcherCache(CacheUserTestCase, TestEntreeUserFetcher):
    pass

class TestAuthMiddlewareCache(CacheUserTestCase, TestAuthMiddleware):
    pass
'''
