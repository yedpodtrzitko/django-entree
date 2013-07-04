from django.conf import settings
from django.core.cache import cache
from django.forms.widgets import CheckboxInput, TextInput
from django.test.testcases import TestCase

from entree.enauth.models import Identity
from entree.host.forms import ProfileForm
from entree.host.models import SiteProperty, EntreeSite, TYPE_BOOL, TYPE_STR, ProfileData, SiteProfile

from nose.tools import assert_raises, assert_equals


ENTREE = settings.ENTREE

class TestProfileForm(TestCase):

    def setUp(self):
        super(TestProfileForm, self).setUp()
        cache.clear()

        self.user = Identity.objects.create(email='foo@bar.cz')
        self.site = EntreeSite.objects.create(title='site title', url='http://foo.cz')

        self.nosite = EntreeSite.objects.create(pk=ENTREE['NOSITE_ID'])

    def test_boolean_field(self):
        prop_name = 'field'
        SiteProperty.objects.create(value_type=TYPE_BOOL, slug=prop_name, site=self.site)

        form = ProfileForm(user=self.user, site=self.site)
        input_class = type(form.fields[prop_name].widget)
        assert_equals(CheckboxInput, input_class)


    def test_char_field(self):
        prop_name = 'field'
        SiteProperty.objects.create(value_type=TYPE_STR, slug=prop_name, site=self.site)

        form = ProfileForm(user=self.user, site=self.site)
        input_class = type(form.fields[prop_name].widget)
        assert_equals(TextInput, input_class)


    def test_load_existing_value_in_form(self):
        NEWVAL = 'fooval'
        prop = SiteProperty.objects.create(site=self.site, slug='foo')
        dato = ProfileData(site_property=prop, user=self.user)
        dato.set_value(NEWVAL)

        form = ProfileForm(user=self.user, site=self.site)

        assert_equals(form.fields[prop.slug].initial, NEWVAL)


    def test_clean_raises_on_unique_violation(self):
        valid_data = {'foo': 'bar'}

        SiteProperty.objects.create(slug='foo', is_unique=True, site=self.site)
        user2 = Identity.objects.create(email='foo2@bar.cz')

        form = ProfileForm(user=self.user, site=self.site, data=valid_data)
        assert_equals(True, form.is_valid())

        form2 = ProfileForm(user=user2, site=self.site, data=valid_data)
        assert_equals(False, form2.is_valid())

    def test_update_existing_value(self):
        prop = SiteProperty.objects.create(slug='foo', is_unique=True, site=self.site)

        NEWVAL = 'foobar'
        dato = ProfileData(site_property=prop, user=self.user)
        dato.set_value('foo')

        valid_data = {'foo':  NEWVAL}

        form = ProfileForm(user=self.user, site=self.site, data=valid_data)
        assert_equals(True, form.is_valid())

        load_dato = ProfileData.objects.get(site_property=prop, user=self.user)
        assert_equals(load_dato.value, NEWVAL)


    def test_clean_flushes_profile_cache(self):
        prop = SiteProperty.objects.create(slug='foo', is_unique=True, site=self.site)

        profile = SiteProfile.objects.create(user=self.user, site=self.site, is_active=True)

        #cache data
        SiteProfile.objects.get_data(user=self.user, site=self.site)


        NEWVAL = 'foobar'
        dato = ProfileData(site_property=prop, user=self.user)
        dato.set_value('foo')

        valid_data = {'foo':  NEWVAL}

        form = ProfileForm(user=self.user, site=self.site, data=valid_data)
        assert_equals(True, form.is_valid())

        changed_data = SiteProfile.objects.get_data(user=self.user, site=self.site)

        assert_equals(NEWVAL, changed_data['foo'])
