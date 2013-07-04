import logging

from django.conf import settings
from django.views.generic.base import RedirectView


logger = logging.getLogger(__name__)
ENTREE = settings.ENTREE


class EntreeRedirectView(RedirectView):
    permanent = False

    @property
    def route(self):
        raise NotImplementedError("Override in child class")

    def get_redirect_url(self, **kwargs):
        ret = "%(url)s/%(route)s/%(site)s/%(next)s/" % {
            'url': ENTREE['URL_SERVER'].rstrip('/'),
            'route': self.route.strip('/'),
            'site': ENTREE['SITE_ID'],
            'next': self.kwargs['return_url'],
        }
        logging.info("redirect url %s" % ret)
        return ret


class EditView(EntreeRedirectView):

    route = ENTREE['ROUTE']['PROFILE_EDIT']


class LoginView(EntreeRedirectView):

    route = ENTREE['ROUTE']['LOGIN']


class RegisterView(EntreeRedirectView):

    route = ENTREE['ROUTE']['REGISTER']


class LogoutView(EntreeRedirectView):

    route = ENTREE['ROUTE']['LOGOUT']

    def get(self, request, *args, **kwargs):
        try:
            del self.request.COOKIES[ENTREE['COOKIE']['NAME']]
        except KeyError:
            pass

        return super(LogoutView, self).get(request, *args, **kwargs)
