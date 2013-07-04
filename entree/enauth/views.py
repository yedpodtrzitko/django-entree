import simplejson as json
import logging
import re

from binascii import Error as DecodeError
from urlparse import urlparse
from base64 import b64decode
from cache_tools.utils import get_cached_object

from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import AnonymousUser
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpResponseRedirect, Http404
from django.views.decorators.cache import never_cache
from django.views.generic.base import View, TemplateView, TemplateResponseMixin
from django.views.generic.edit import FormView, CreateView
from django.shortcuts import render_to_response
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.template.context import RequestContext

from entree.enauth.forms import EntreeAuthForm, CreateIdentityForm, RecoveryForm, LogoutForm, BasicPasswordForm, ChangePasswordForm
from entree.enauth.mailer import IdentityMailer
from entree.enauth.models import Identity, LoginToken, MAIL_TOKEN, AUTH_TOKEN, RESET_TOKEN
from entree.enauth.middleware import CACHED_USER_KEY
from entree.common.views import JSONResponseMixin
from entree.common.utils import ENTREE_SAFE
from entree.host.views import get_next_url, AuthRequiredMixin
from entree.host.models import EntreeSite, SiteProfile


ENTREE = settings.ENTREE
logger = logging.getLogger(__name__)


class EntreeAuthMixin(TemplateResponseMixin):
    def entree_login(self, identity, site_id=None, next_url=None):
        sess = self.request.session

        if SESSION_KEY not in sess:
            sess.cycle_key()
        elif ENTREE['SESSION_KEY'] in sess and sess[ENTREE['SESSION_KEY']] != identity.id:
            sess.flush()

        token = identity.create_token(app_data={'session': sess.session_key})
        sess[ENTREE['SESSION_KEY']] = identity.id
        sess[ENTREE['STORAGE_TOKEN_KEY']] = token.value

        self.request.entree_user = identity

        #can we redirect back to origin site or do we need activate profile first?
        if site_id:
            try:
                active = SiteProfile.objects.get(site_id=site_id, user=identity).is_active
            except SiteProfile.DoesNotExist:
                active = False

            if not active:
                kwargs = dict(site_id=site_id)
                if next_url:
                    kwargs.update(dict(next_url=next_url))

                #TODO - cleanup
                if 'entree.host.profiles' in settings.INSTALLED_APPS:
                    next_url = reverse('profile_edit', kwargs=kwargs)
                else:
                    next_url = reverse('profile')
            else:
                next_url = get_next_url(site_id, next_url)

        return render_to_response('post_login.html', {
            'next_url': next_url,
            'user_token': token.value,
            }, context_instance=RequestContext(self.request))

    def entree_logout(self, next_url=None):
        """
        - delete request[ -ENTREE_USER- ]
        - delete request[ -CACHED_USER_KEY- ]
        - delete request.session[ -ENTREE_SESSION_KEY- ]
        - delete LoginToken (cache's flush is handled in LoginToken.delete())
        - remove token from LocalStorage (via logout.html)
        """
        request = self.request
        if request.entree_user.is_authenticated():
            old_user = request.entree_user
            try:
                token = LoginToken.objects.get(
                    value=request.session.get(ENTREE['STORAGE_TOKEN_KEY']),
                    user=old_user,
                    token_type=AUTH_TOKEN)
            except LoginToken.DoesNotExist:
                pass
            else:
                token.delete()

            request.entree_user = AnonymousUser()

        try:
            delattr(request, CACHED_USER_KEY)
        except (AttributeError, KeyError):
            pass

        for one in (ENTREE['SESSION_KEY'], ENTREE['STORAGE_TOKEN_KEY']):
            if one in request.session:
                del request.session[one]

        next_url = next_url or '/'
        return HttpResponseRedirect(next_url)


class LoginView(EntreeAuthMixin, FormView):

    template_name = 'login.html'
    form_class = EntreeAuthForm

    @never_cache
    def dispatch(self, request, *args, **kwargs):
        if not kwargs.get('origin_site'):
            try:
                origin_site = get_cached_object(EntreeSite, is_default=True)
            except EntreeSite.DoesNotExist:
                raise Http404("No default client site set")

            url = reverse('login', kwargs={
                'origin_site': origin_site.pk,
            })
            return HttpResponseRedirect(url)

        if request.entree_user.is_authenticated():
            edit_kwargs = {
                'site_id': int(kwargs['origin_site']),
            }
            if kwargs.get('next_url'):
                edit_kwargs['next_url'] = kwargs['next_url']

            # TODO - cleanup
            if 'entree.host.profiles' in settings.INSTALLED_APPS:
                url = reverse('profile_edit', kwargs=edit_kwargs)
            else:
                url = reverse('profile')

            return HttpResponseRedirect(url)

        return super(LoginView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super(LoginView, self).get_context_data(**kwargs)
        data['origin_site'] = get_cached_object(EntreeSite, pk=self.kwargs['origin_site'])
        return data

    def form_valid(self, form):
        return self.entree_login(form.get_user(), self.kwargs['origin_site'], self.kwargs.get('next_url'))


class LogoutView(AuthRequiredMixin, EntreeAuthMixin, FormView):

    form_class = LogoutForm
    template_name = 'logout.html'

    def form_valid(self, form):
        origin_site = self.kwargs.get('origin_site', ENTREE['DEFAULT_SITE'])
        next_url = get_next_url(origin_site, self.kwargs.get('next_url'))
        return self.entree_logout(next_url)


class LoginHashView(TemplateView):

    template_name = 'iframe_auth.html'

    @never_cache
    def get(self, request, *args, **kwargs):
        valid_sites = []
        for one in EntreeSite.objects.active():
            domain = urlparse(one.url).hostname
            if domain:
                valid_sites.append(domain)

        if not valid_sites:
            logger.warning("There are no active sites, users can't be logged in")

        return self.render_to_response({
            'domains_whitelist': valid_sites,
            'entree': ENTREE_SAFE,
        })


class CreateIdentityView(EntreeAuthMixin, CreateView):

    model = Identity
    template_name = 'register.html'
    form_class = CreateIdentityForm

    def dispatch(self, request, *args, **kwargs):
        if not kwargs.get('origin_site'):
            raise Http404("missing site id")
        return super(CreateIdentityView, self).dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('profile')

    def get(self, request, *args, **kwargs):
        return super(CreateIdentityView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super(CreateIdentityView, self).get_context_data(**kwargs)
        data['origin_site'] = get_cached_object(EntreeSite, pk=self.kwargs['origin_site'])
        return data

    def form_valid(self, form):
        """
        If form is valid, send activation email and login user
        """
        super(CreateIdentityView, self).form_valid(form)

        mailer = IdentityMailer(self.object)
        mailer.send_activation()

        token = mailer.token
        token.app_data.entree['origin_site'] = self.kwargs['origin_site']
        token.app_data.entree['next_url'] = self.kwargs.get('next_url')
        token.save()

        return self.entree_login(self.object)


class IdentityVerifyView(EntreeAuthMixin, TemplateView):

    template_name = 'verify_notice.html'

    def get(self, request, *args, **kwargs):
        if not (kwargs.get('email') and kwargs.get('token')):
            return super(IdentityVerifyView, self).get(request, *args, **kwargs)

        try:
            email = b64decode(kwargs['email'])
            validate_email(email)

            str_token = re.sub('[^A-Z0-9]+', '', kwargs['token'])

            token = LoginToken.objects.get(user__email=email, token_type=MAIL_TOKEN, value=str_token)
        except (LoginToken.DoesNotExist, ValidationError, UnicodeError, DecodeError):
            return super(IdentityVerifyView, self).get(request, *args, **kwargs)

        site_id = token.app_data.entree.get('origin_site')
        next_url = token.app_data.entree.get('next_url')

        identity = token.user
        identity.is_active = identity.mail_verified = True
        identity.save()

        token.delete()

        try:
            response = self.entree_login(identity, site_id, next_url)
        except Exception:
            logger.error("Identity login failed")
            return HttpResponseRedirect(reverse('login'))
        else:
            messages.success(self.request, _("Splendid! Your account successfully activated"))
            return response


class IdentityVerifyResend(AuthRequiredMixin, JSONResponseMixin):

    def get(self, request, *args, **kwargs):
        mailer = IdentityMailer(request.entree_user)
        try:
            send_status = mailer.send_activation()
        except ValidationError:
            send_status = False

        if request.is_ajax():
            return self.render_to_response({'send_status': send_status})

        return HttpResponseRedirect(reverse("verify_identity"))


class RecoveryLoginView(EntreeAuthMixin, View):
    """
    Login recovery. Used if there's a value in LocalStorage (LS), but user lost his session cookie,
        If so, take LS value and redirect in here and look for matching LoginToken.
            If token is found, everyone can be happy.
            If not, delete LS value and show loginform again
    """

    @never_cache
    def get(self, request, *args, **kwargs):
        token_str = request.GET.get('token')
        token_str = re.sub('[^A-Z0-9]+', '', token_str)

        try:
            token = LoginToken.objects.get(value=token_str, token_type=AUTH_TOKEN)
        except LoginToken.DoesNotExist:
            next_url = reverse('login', kwargs={
                'origin_site': kwargs.get('origin_site', ENTREE['DEFAULT_SITE'])
            })

            return render_to_response('delete_token.html', {
                'entree': ENTREE_SAFE,
                'input_token': token_str,
                'next_url': next_url,
            }, context_instance=RequestContext(request))
        else:
            return self.entree_login(token.user, site_id=kwargs.get('origin_site'))


class PasswordRecoveryRequestView(FormView):

    form_class = RecoveryForm
    template_name = 'recover_request.html'

    def get_success_url(self):
        return reverse('recovery_finish')


class FinishRecoveryView(TemplateView):

    template_name = 'recover_finish.html'


class PasswordChangeView(AuthRequiredMixin, FormView):

    form_class = ChangePasswordForm
    template_name = 'password_change.html'

    def get_success_url(self):
        return reverse('profile')

    def get_form_kwargs(self):
        kwargs = super(PasswordChangeView, self).get_form_kwargs()
        kwargs['entree_user'] = self.request.entree_user
        return kwargs

    def form_valid(self, form):
        actual_token = self.request.session[ENTREE['STORAGE_TOKEN_KEY']]
        LoginToken.objects \
            .filter(user=self.request.entree_user, token_type=AUTH_TOKEN) \
            .exclude(value=actual_token).delete()

        self.request.entree_user.set_password(form.cleaned_data['password'])
        self.request.entree_user.save()

        messages.success(self.request, _("Password successfully changes"))

        return super(PasswordChangeView, self).form_valid(form)


class PasswordResetView(FormView):

    form_class = BasicPasswordForm
    template_name = 'recover_changeform.html'

    def dispatch(self, request, *args, **kwargs):
        if ('email' in kwargs and 'token' in kwargs) and not self.is_token_valid(**kwargs):
            return HttpResponseRedirect(reverse('password_recovery'))

        return super(PasswordResetView, self).dispatch(request, *args, **kwargs)

    def is_token_valid(self, token, email):
        try:
            email = b64decode(email)
            validate_email(email)

            token_str = re.sub('[^A-Z0-9]+', '', token)

            return LoginToken.objects.get(user__email=email, token_type=RESET_TOKEN, value=token_str)
        except (LoginToken.DoesNotExist, ValidationError, UnicodeError, DecodeError):
            logger.info("Change password form requested with invalid token")
            return False

    def form_valid(self, form):
        token = self.is_token_valid(**self.kwargs)
        token.user.set_password(form.cleaned_data['password'])
        token.user.save()

        LoginToken.objects.filter(token_type=AUTH_TOKEN, user=token.user).delete()
        token.delete()

        return HttpResponseRedirect(reverse('login'))


class ShowApiView(TemplateView):

    template_name = 'api/show.html'

    def get_context_data(self, **kwargs):
        data = super(ShowApiView, self).get_context_data(**kwargs)
        REPLACE_STR = "REPLACE_ME"
        REPLACE_INT = 123456789

        if 'site_id' in kwargs:
            site = EntreeSite.objects.get(pk=int(kwargs['site_id']))
            SITE_ID = site.pk
            DOMAIN = urlparse(site.url).hostname
        else:
            SITE_ID = REPLACE_INT
            DOMAIN = REPLACE_STR

        prepare_entree = {
            "VERSION": ENTREE['VERSION'],
            'URL_SERVER': ENTREE['URL_SERVER'],
            'CACHE_PROFILE': 5*60,
            'ROUTE': {
                'LOGIN': reverse('login'),
                'LOGOUT': reverse('logout'),
                'REGISTER': reverse('register'),
                'PROFILE': reverse('profile'),
                'PROFILE_EDIT': reverse('profile_edit'),
                'PROFILE_FETCH': reverse('profile_fetch'),
                'JS_LIB': settings.STATIC_URL + 'js/entree.js',
            },
            'COOKIE': {
                'ANONYMOUS_VALUE': 'ANONYMOUS',
                'NAME': 'entree_token',
                'DOMAIN': DOMAIN,
                'PATH': '/',
                'INVALID': 'INVALID',
            },
            'SITE_ID': SITE_ID,
            'SECRET_KEY': REPLACE_STR,
        }

        prepare_entree = json.dumps(prepare_entree, indent=4)
        prepare_entree = prepare_entree.replace(str(REPLACE_INT), '<strong>%s</strong>' % REPLACE_INT)
        prepare_entree = prepare_entree.replace('"%s"' % REPLACE_STR, '<strong>%s</strong>' % REPLACE_STR)

        data['ENTREE'] = mark_safe(prepare_entree)

        return data
