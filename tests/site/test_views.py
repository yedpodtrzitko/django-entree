from base64 import b64encode
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.http import Http404
from django.test.testcases import TestCase
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from entree.user.managers import EntreeUserFetcherMixin
from entree.common.utils import calc_checksum, SHORT_CHECK
from entree.enauth.models import Identity
from entree.host.forms import ProfileForm
from entree.host.models import EntreeSite, SiteProfile, SiteProperty, ProfileData
from entree.host.views import ProfileView, ProfileFetchView, ProfileEdit

from nose.tools import assert_raises, assert_equals
from tests.auth.test_views import init_request


ENTREE = settings.ENTREE


class TestViews(TestCase):

    def setUp(self):
        super(TestViews, self).setUp()
        cache.clear()

        self.request = init_request()

        self.user = Identity.objects.create(email='foo@bar.cz')

        self.valid_site = EntreeSite.objects.create(id=ENTREE['SITE_ID'], title='foo', is_active=True, secret='mysecretkey', url="http://foobar.cz")
        self.nosite = EntreeSite.objects.create(id=ENTREE['NOSITE_ID'], title='nosite', is_active=True, secret='mysecretkey', url="http://nosite.cz")

    def test_auth_required_return_200(self):
        self.request.entree_user = self.user

        ViewClass = ProfileView.as_view()
        view = ViewClass(self.request)

        assert_equals(200, view.status_code)

    def test_auth_required_redirect_anonymous(self):
        self.request.entree_user = AnonymousUser()

        ViewClass = ProfileView.as_view()
        view = ViewClass(self.request)

        assert_equals(302, view.status_code)
        assert_equals(view['Location'], reverse('login'))

    def test_fetch_profile_post_no_data_403(self):

        self.request.method = 'POST'

        ViewClass = ProfileFetchView.as_view()
        view = ViewClass(self.request)

        assert_equals(403, view.status_code)

    def test_fetch_profile_post_wrong_site_403(self):

        self.valid_site.secret = ENTREE['SECRET_KEY']
        self.valid_site.save()

        fetcher = EntreeUserFetcherMixin()
        token = self.user.create_token()

        fetch_params = fetcher._fetch_params(token.value)

        self.valid_site.delete()

        self.request.method = 'POST'
        self.request.POST = fetch_params

        ViewClass = ProfileFetchView.as_view()
        view = ViewClass(self.request)

        assert_equals(403, view.status_code)

    def test_fetch_profile_post_unknown_token_403(self):

        self.valid_site.secret = ENTREE['SECRET_KEY']
        self.valid_site.save()

        fetcher = EntreeUserFetcherMixin()
        token = self.user.create_token()

        fetch_params = fetcher._fetch_params(token.value)

        token.delete()

        self.request.method = 'POST'
        self.request.POST = fetch_params

        ViewClass = ProfileFetchView.as_view()
        view = ViewClass(self.request)

        assert_equals(403, view.status_code)


    def test_fetch_profile_inactive_site_403(self):
        self.valid_site.is_active = False
        self.valid_site.secret = ENTREE['SECRET_KEY']
        self.valid_site.save()

        fetcher = EntreeUserFetcherMixin()
        token = self.user.create_token()

        fetch_params = fetcher._fetch_params(token.value)

        self.request.method = 'POST'
        self.request.POST = fetch_params

        ViewClass = ProfileFetchView.as_view()
        view = ViewClass(self.request)

        assert_equals(403, view.status_code)

    def test_fetch_profile_invalid_checksum_403(self):
        self.valid_site.secret = ENTREE['SECRET_KEY']
        self.valid_site.save()

        fetcher = EntreeUserFetcherMixin()
        token = self.user.create_token()

        fetch_params = fetcher._fetch_params(token.value)
        fetch_params['checksum'] = 'foo'

        self.request.method = 'POST'
        self.request.POST = fetch_params

        ViewClass = ProfileFetchView.as_view()
        view = ViewClass(self.request)

        assert_equals(403, view.status_code)

    def test_fetch_profile_post_good_data_200(self):
        self.valid_site.secret = ENTREE['SECRET_KEY']
        self.valid_site.save()

        fetcher = EntreeUserFetcherMixin()
        token = self.user.create_token()

        fetch_params = fetcher._fetch_params(token.value)

        self.request.method = 'POST'
        self.request.POST = fetch_params

        ViewClass = ProfileFetchView.as_view()
        view = ViewClass(self.request)

        assert_equals(200, view.status_code)

    def test_edit_profile_no_site_id_raises_404(self):
        ViewClass = ProfileEdit.as_view()
        assert_raises(Http404, lambda: ViewClass(self.request))

    def test_edit_profile_no_auth_user_redirects_to_login(self):
        self.request.entree_user = AnonymousUser()

        ViewClass = ProfileEdit.as_view()
        view = ViewClass(self.request, site_id=self.valid_site.pk)

        assert_equals(302, view.status_code)
        assert_equals(view['Location'], reverse('login'))

    def test_edit_profile_anonymous_restricted(self):

        ViewClass = ProfileEdit.as_view()
        view = ViewClass(self.request, site_id=self.valid_site.pk)

        assert_equals(302, view.status_code)

    def test_auth_required_mixin_anon_user_in_request(self):
        ViewClass = ProfileEdit.as_view()
        view = ViewClass(self.request, site_id=self.valid_site.pk)

        assert_equals(302, view.status_code)
        assert_equals(view['Location'], reverse('login'))

    def test_edit_profile_user_allowed(self):
        self.request.entree_user = self.user

        ViewClass = ProfileEdit.as_view()
        view = ViewClass(self.request, site_id=self.valid_site.pk)

        assert_equals(200, view.status_code)

    def test_edit_profile_invalid_site_id_raises_404(self):
        ViewClass = ProfileEdit.as_view()
        assert_raises(Http404, lambda: ViewClass(self.request, site_id=self.valid_site.pk+10))

    def test_edit_profile_form_redirects_to_profile_list(self):
        self.request.entree_user = self.user
        self.request.method = 'POST'
        self.request.POST = {}

        ViewClass = csrf_exempt(ProfileEdit.as_view())
        res = ViewClass(self.request, site_id=self.valid_site.pk, next_url='')

        print dir(res)
        print res
        assert_equals(res['Location'], reverse('profile'))

        profile = SiteProfile.objects.get(user=self.user, site=self.valid_site)
        assert profile

    def test_edit_profile_form_valid_no_next_url_redirect_profile(self):
        self.request.entree_user = self.user
        self.request.method = 'POST'
        self.request.POST = {}

        ViewClass = csrf_exempt(ProfileEdit.as_view())
        res = ViewClass(self.request, site_id=self.valid_site.pk)

        assert_equals(res['Location'], reverse('profile'))

    def test_edit_profile_form_valid_next_url_redirect_there(self):
        self.request.entree_user = self.user
        self.request.method = 'POST'
        self.request.POST = {}

        next_url = '/foo/'
        checked_url = "%s:%s" % (next_url, calc_checksum(next_url, salt=self.valid_site.secret, length=SHORT_CHECK))

        ViewClass = csrf_exempt(ProfileEdit.as_view())
        res = ViewClass(self.request, site_id=self.valid_site.pk, next_url=b64encode(checked_url))

        location = "%s%s" % (self.valid_site.url, next_url)

        assert_equals(res['Location'], location)

    def test_save_profile_invalidates_cache(self):
        prop = SiteProperty.objects.create(slug='foo', site=self.valid_site)

        NEWVAL = 'fooval'
        self.request.entree_user = self.user
        self.request.method = 'POST'
        self.request.POST = {
            prop.slug: NEWVAL
        }

        ViewClass = csrf_exempt(ProfileEdit.as_view())
        ViewClass(self.request, site_id=self.valid_site.pk, next_url='')

        data = ProfileData.objects.get(site_property=prop, user=self.user)
        assert_equals(data.value, NEWVAL)

        form = ProfileForm(user=self.user, site=self.valid_site)
        assert_equals(form.fields[prop.slug].initial, NEWVAL)
