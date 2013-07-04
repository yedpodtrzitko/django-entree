# -*- coding: utf-8 -*-
from base64 import b64encode

from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.test.testcases import TestCase
from django.conf import settings

from entree.enauth.models import Identity
from entree.common.utils import calc_checksum, SHORT_CHECK
from entree.host.models import EntreeSite
from entree.host.views import get_next_url

from nose.tools import assert_raises, assert_equals


ENTREE = settings.ENTREE


class TestSiteManagers(TestCase):

    def setUp(self):
        super(TestSiteManagers, self).setUp()
        cache.clear()

    def tearDown(self):
        super(TestSiteManagers, self).tearDown()

        EntreeSite.objects.all().delete()

    def test_get_no_active_sites(self):
        EntreeSite.objects.create(is_active=False, pk=settings.ENTREE['NOSITE_ID']+1)

        qs = EntreeSite.objects.active()
        assert_equals(0, len(qs))

    def test_get_one_active_site(self):
        site = EntreeSite.objects.create(is_active=True, pk=settings.ENTREE['NOSITE_ID']+1)

        qs = EntreeSite.objects.active()
        assert_equals(site, qs[0])
        assert_equals(1, len(qs))

    def test_active_ignores_default_site(self):
        site = EntreeSite(is_active=True, pk=settings.ENTREE['NOSITE_ID'])
        site.save()

        qs = EntreeSite.objects.active()
        assert_equals(0, len(qs))

    def test_cache_and_retrieve(self):

        EntreeSite.objects.set_cached('foo', 'bar')
        retrieved = EntreeSite.objects.get_cached('foo')
        assert_equals('bar', retrieved)



class TestNextUrl(TestCase):

    def setUp(self):
        self.user = Identity.objects.create(email='foo@bar.cz')
        self.valid_site = EntreeSite.objects.create(id=ENTREE['SITE_ID'], title='foo', is_active=True, secret=ENTREE['SECRET_KEY'], url="http://foobar.cz")

    def test_next_url_bad_origin_site_redirects(self):
        ret = get_next_url(origin_site=self.valid_site.pk+1, next_url='/foobar/')
        assert_equals(ret, reverse('profile'))

    def test_next_url_no_origin_site_redirects(self):
        ret = get_next_url(origin_site=self.valid_site.pk+1)
        assert_equals(ret, reverse('profile'))

    def test_next_url_invalid_post_login_pacified(self):
        ret = get_next_url(self.valid_site.pk, b64encode(''))
        assert_equals(ret.rstrip('/'), self.valid_site.url)

    def test_next_url_valid_checksum_return_input_url(self):
        url = '/foo/'
        next_url = b64encode("%s:%s" % (url, calc_checksum(url, length=SHORT_CHECK) ) )
        ret = get_next_url(self.valid_site.pk, next_url)
        assert_equals(ret, "%s%s" % (self.valid_site.url, url))

    def test_next_url_no_checksum_return_root(self):
        url = '/foo/'
        ret = get_next_url(self.valid_site.pk, b64encode(url))
        assert_equals(ret.rstrip('/'), self.valid_site.url.rstrip('/'))

    def test_next_url_invalid_checksum_return_root(self):
        url = '/foo/'
        next_url = b64encode("%s:%sINVALID" % (url, calc_checksum(url, length=SHORT_CHECK) ) )
        ret = get_next_url(self.valid_site.pk, next_url)
        assert_equals(ret.rstrip('/'), self.valid_site.url.rstrip('/'))
