import logging

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.contrib.auth.models import AnonymousUser
from django.conf import settings

from entree.enauth.backends import AuthBackend


logger = logging.getLogger(__name__)
CACHED_USER_KEY = '_entree_cached_user'


def get_user(request):
    if not getattr(request, CACHED_USER_KEY, None):
        user = AnonymousUser()
        try:
            user_id = request.session[settings.ENTREE['SESSION_KEY']]
        except KeyError:
            pass
        else:
            user = AuthBackend().get_user(user_id) or AnonymousUser()

        setattr(request, CACHED_USER_KEY, user)

    return getattr(request, CACHED_USER_KEY)


class AuthMiddleware(object):
    def process_request(self, request):
        print 'processing request'
        assert hasattr(request, 'session'), "The Django authentication middleware requires session middleware to be installed. Edit your MIDDLEWARE_CLASSES setting to insert 'django.contrib.sessions.middleware.SessionMiddleware'."
        user = get_user(request)
        request.__class__.entree_user = user

        #do not allow user w/o verified go anywhere
        if user.is_authenticated():
            if user.mail_verified and user.is_active:
                return None

            if request.path.startswith(reverse('logout')):
                return None

            redirect_path = reverse('verify_identity')
            if not request.path.startswith(redirect_path):
                return HttpResponseRedirect(redirect_path)
