# -*- coding: utf-8 -*-
from django.db import IntegrityError
from django.test.testcases import TestCase
from django.core.cache import cache
from django.conf import settings
from entree.enauth.models import Identity

from entree.host.models import SiteProfile, EntreeSite, SiteProperty, ProfileData, ProfileDataUnique, TYPE_INT, TYPE_BOOL

from nose.tools import assert_raises, assert_equals


ENTREE = settings.ENTREE


class TestSiteProperty(TestCase):

    def setUp(self):
        super(TestSiteProperty, self).setUp()
        cache.clear()
        self.site = EntreeSite.objects.create(title=u'ěfoosite')
        self.nosite = EntreeSite.objects.create(id=ENTREE['NOSITE_ID'])

    def tearDown(self):
        super(TestSiteProperty, self).tearDown()
        SiteProperty.objects.all().delete()

    def test_property_unicode_serialize(self):
        #coverage ftw
        prop_name = u'žprop name'
        prop = SiteProperty.objects.create(site=self.site, name=prop_name)

        assert prop_name in unicode(prop)
        assert unicode(self.site) in unicode(prop)

    def test_property_cache_invalidation_for_siteprofile(self):
        no_props = SiteProperty.objects.get_site_props(site=self.site)
        assert_equals([], no_props)

        prop = SiteProperty.objects.create(site=self.site, name='foo')
        props = SiteProperty.objects.get_site_props(site=self.site)
        assert_equals([prop], props)


    def test_save_prop_with_existing_slug_in_resident_raises(self):

        SiteProperty.objects.create(site=self.nosite, slug='foo')

        assert_raises(IntegrityError, lambda: SiteProperty.objects.create(site=self.site, slug='foo'))


    def test_delete_signal_remove_relevant_profiledata(self):

        prop = SiteProperty.objects.create(site=self.site, slug='foo')
        user = Identity.objects.create(email='foo@bar.cz')

        NEWVAL = 'foobar'

        dato = ProfileData(site_property=prop, user=user)
        dato.set_value(NEWVAL)

        prop.delete()

        assert_equals([], list(ProfileData.objects.all()))


class TestSiteProfile(TestCase):

    def setUp(self):
        super(TestSiteProfile, self).setUp()
        cache.clear()

        #properties map
        self.properties = dict(
            is_active='is_active',
            site_name='site_prop',
            generic_name='generic_prop',
        )

        self.nosite = EntreeSite.objects.create(id=ENTREE['NOSITE_ID'])
        self.site = EntreeSite.objects.create(title=u'site_a unicodé', url='http://site_a')

        self.site_prop = SiteProperty.objects.create(
            name=u'únícodé námé',
            slug=self.properties['site_name'],
            site=self.site)

        self.nosite_prop = SiteProperty.objects.create(
            name=self.properties['generic_name'],
            slug=self.properties['generic_name'],
            site=self.nosite)

        self.user = Identity.objects.create(email='baz@bar.cz')

        self.user_default_profile = SiteProfile.objects.create(
            user=self.user,
            site=self.nosite,
            is_active=True
        )

        self.user_site_data = {
            'baz':  u"ignored_as_it's_not_defined_property unicodé",
            self.properties['site_name']: u'proper_site_property unicodé',
        }

        self.user_site_profile = SiteProfile.objects.create(
            user=self.user,
            site=self.site,
            is_active=True
        )

    def test_get_user_data_without_profile(self):
        expected_data = [self.properties['is_active']]

        user = Identity.objects.create(email='xxx@bar.cz')

        obtained_data = SiteProfile.objects.get_data(user=user).keys()
        assert_equals(obtained_data, expected_data)

    def test_get_user_data_without_profile_with_site_defined(self):
        #expect merged generic + site-specific properties
        expected_data = {self.properties['is_active']: False}

        user = Identity.objects.create(email='xxx@bar.cz')

        obtained_data = SiteProfile.objects.get_data(user=user, site=self.site)
        assert_equals(expected_data, obtained_data)


    def test_get_site_profile_for_user(self):
        expected_data = set( self.properties.values() )
        obtained_data = set( map(str, SiteProfile.objects.get_data(user=self.user, site=self.site).keys()) )
        assert_equals(expected_data, obtained_data)

    def test_get_default_profile_for_user_with_site_profile(self):
        #expect to get defined generic property only
        expected_data = set( [self.properties['generic_name'], self.properties['is_active']] )
        obtained_data = set( map(str, SiteProfile.objects.get_data(user=self.user).keys()) )
        assert_equals(expected_data, obtained_data)

    def test_profile_unicode_pass(self):
        profile = SiteProfile(user=self.user, site=self.site)
        assert_equals(True, self.site.title in unicode(profile))

    def test_get_cached_data_cached_itself_if_isnt_yet(self):

        NEW_VAL = 'foobar'
        data = ProfileData.objects.create(user=self.user, site_property=self.site_prop)
        data.set_value(NEW_VAL)

        site_data = SiteProfile.objects.get_data(user=self.user, site=self.site)

        expected_data = set( [self.site_prop.slug, self.nosite_prop.slug, 'is_active' ] )
        assert_equals(set( site_data.keys() ), expected_data)
        assert_equals(site_data[self.site_prop.slug], NEW_VAL)

    def test_profile_data_unicode_pass(self):
        #coverage ftw

        name = u'námé únícódé'
        p_data = ProfileData(user=self.user, site_property=self.site_prop)
        assert_equals(True, self.site_prop.name in unicode(p_data))

    def test_profile_data_save_long_string(self):

        dato_long_str = 's' * 50

        dato = ProfileData(user=self.user, site_property=self.site_prop)
        dato.set_value(dato_long_str, self.site_prop.value_type)

        assert_equals(dato.value_str, None)
        assert_equals(dato.value_big.value, dato_long_str)
        assert_equals(dato.value, dato_long_str)

    def test_profile_data_update_long_string(self):

        dato_long_str = 's' * 50

        dato = ProfileData(user=self.user, site_property=self.site_prop)
        dato.set_value(dato_long_str, self.site_prop.value_type)

        dato.set_value(dato_long_str*2)
        assert_equals(dato.value_big.value, dato_long_str*2)


    def test_profile_data_save_short_str(self):

        dato_short_str = 's' * 10

        dato = ProfileData(user=self.user, site_property=self.site_prop)
        dato.set_value(dato_short_str, self.site_prop.value_type)

        assert_equals(dato.value, dato_short_str)
        assert_equals(dato.value_str, dato_short_str)
        assert_equals(dato.value_big, None)

    def test_profile_data_save_int(self):

        data_int = 50

        prop = SiteProperty.objects.create(value_type=TYPE_INT, slug='prop', site=self.site)

        dato = ProfileData(user=self.user, site_property=prop)
        dato.set_value(data_int, prop.value_type)

        assert_equals(dato.value, data_int)

    def test_profile_data_update_int(self):

        data_int = 50

        prop = SiteProperty.objects.create(value_type=TYPE_INT, slug='prop', site=self.site)

        dato = ProfileData(user=self.user, site_property=prop)
        dato.set_value(data_int, prop.value_type)

        dato.set_value(data_int*2)
        assert_equals(dato.value_int, data_int*2)

    def test_profile_data_save_bool(self):

        data_bool = 50

        prop = SiteProperty.objects.create(value_type=TYPE_BOOL, slug='prop', site=self.site)

        dato = ProfileData(user=self.user, site_property=prop)
        dato.set_value(data_bool, prop.value_type)

        assert_equals(dato.value, data_bool)

    def test_profile_data_update_bool(self):

        data_bool = True

        prop = SiteProperty.objects.create(value_type=TYPE_BOOL, slug='prop', site=self.site)

        dato = ProfileData(user=self.user, site_property=prop)
        dato.set_value(data_bool, prop.value_type)

        dato.set_value(not data_bool)
        assert_equals(dato.value_bool, not data_bool)


    def test_profile_data_unique_save_int(self):

        data_int = 50

        prop = SiteProperty.objects.create(value_type=TYPE_INT, slug='prop', site=self.site)

        dato = ProfileDataUnique(user=self.user, site_property=prop)
        dato.set_value(data_int, prop.value_type)

        assert_equals(dato.value_str, None)
        assert_equals(dato.value_int, data_int)
        assert_equals(dato.value, data_int)

    def test_profile_data_qunieue_update_int(self):

        data_int = 50

        prop = SiteProperty.objects.create(value_type=TYPE_INT, slug='prop', site=self.site)

        dato = ProfileDataUnique(user=self.user, site_property=prop)
        dato.set_value(data_int, prop.value_type)

        dato.set_value(data_int*2)
        assert_equals(dato.value_int, data_int*2)
