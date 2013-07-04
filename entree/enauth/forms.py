from app_data import AppDataForm, multiform_factory

from django import forms
from django.utils.translation import ugettext_lazy as _

from entree.enauth.backends import AuthBackend
from entree.enauth.mailer import IdentityMailer
from entree.enauth.models import Identity, LoginToken


class EntreeAuthForm(forms.Form):
    username = forms.CharField(label=_("Username"), max_length=60)
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super(EntreeAuthForm, self).__init__(*args, **kwargs)

    def clean(self):
        data = self.cleaned_data
        if 'username' in data and 'password' in data:
            self.user_cache = AuthBackend().authenticate(username=data['username'], password=data['password'])
            if not self.user_cache:
                raise forms.ValidationError(_("Please enter a correct username and password. Note that both fields are case-sensitive."))

            #if not self.user_cache.is_active:
            #    raise forms.ValidationError(_("Account inactive, use confirmation link in email first."))

        self.check_for_test_cookie()
        return self.cleaned_data

    def check_for_test_cookie(self):
        if self.request and not self.request.session.test_cookie_worked():
            raise forms.ValidationError(
                _("Your Web browser doesn't appear to have cookies enabled. "
                  "Cookies are required for logging in."))

    def get_user_id(self):
        return self.user_cache.id if self.user_cache else None

    def get_user(self):
        return self.user_cache


class CreateIdentityForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label=_("Password"))
    password2 = forms.CharField(widget=forms.PasswordInput, label=_("Password again"))

    class Meta:
        model = Identity
        fields = ('email', 'password', 'password2',)

    def clean_password2(self):
        data = self.cleaned_data
        if not data.get('password', "") == data.get('password2', False):
            raise forms.ValidationError(_("Both password fields should match"))

        return data['password2']

    def save(self, commit=True):
        user = super(CreateIdentityForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class RecoveryForm(forms.Form):
    email = forms.EmailField(max_length=100, label=_("E-mail address"))

    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            identity = Identity.objects.get(email=email)
        except Identity.DoesNotExist:
            raise forms.ValidationError(_("Given email is not attached to any user account"))

        mailer = IdentityMailer(identity)
        if not mailer.send_pwd_reset_verify():
            raise forms.ValidationError(_("Unable to send reset email at this time, try later."))

        return email


class LogoutForm(forms.Form):
    pass


class BasicPasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput, label=_("New password"))
    password2 = forms.CharField(widget=forms.PasswordInput, label=_("New password"))

    def clean_password2(self):
        data = self.cleaned_data
        if not data.get('password', "") == data.get('password2', False):
            raise forms.ValidationError(_("Both password fields should match"))

        return data['password2']


class ChangePasswordForm(BasicPasswordForm):
    old_password = forms.CharField(widget=forms.PasswordInput, label=_("Old password"))

    class Meta:
        layout = ('old_password', 'password', 'password2')

    def __init__(self, *args, **kwargs):
        self.entree_user = kwargs.pop('entree_user')
        super(ChangePasswordForm, self).__init__(*args, **kwargs)

    def clean_old_password(self):
        data = self.cleaned_data

        if not self.entree_user.check_password(data['old_password']):
            raise forms.ValidationError("Old password does not match")


class EntreeDataForm(AppDataForm):
    next_url = forms.CharField(required=False)
    origin_site = forms.IntegerField(required=False)


TokenData = multiform_factory(LoginToken, app_data_field='app_data')
TokenData.add_form('entree')
