from cache_tools.utils import get_cached_object
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.views.generic import FormView
from entree.host.models import SiteProfile, EntreeSite
from entree.host.profiles.forms import ProfileForm
from entree.host.views import get_next_url, AuthRequiredMixin


class ProfileEdit(AuthRequiredMixin, FormView):
    template_name = 'profile_edit.html'
    form_class = ProfileForm

    def dispatch(self, request, *args, **kwargs):
        try:
            self.site = get_cached_object(EntreeSite, pk=kwargs['site_id'])
        except (KeyError, EntreeSite.DoesNotExist):
            raise Http404(_("Requested site doesn't exist"))

        return super(ProfileEdit, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        data = super(ProfileEdit, self).get_form_kwargs()
        data.update({
            'site': self.site,
            'user': self.request.entree_user,
        })
        return data

    def get_context_data(self, **kwargs):
        profile, created = SiteProfile.objects.get_or_create(site=self.site, user=self.request.entree_user)

        data = super(ProfileEdit, self).get_context_data(**kwargs)
        data.update({
            'site': self.site,
            'is_active': profile.is_active
        })
        return data

    def form_valid(self, form):
        messages.success(self.request, _("Changes successfully saved"))

        next_url = self.kwargs.get('next_url')
        if not next_url:
            return HttpResponseRedirect(reverse('profile'))

        return HttpResponseRedirect(get_next_url(self.kwargs['site_id'], next_url))

