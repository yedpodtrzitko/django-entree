import logging

from django.contrib.auth.backends import ModelBackend
from entree.enauth.models import Identity

logger = logging.getLogger(__name__)


class AuthBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        try:
            user = Identity.objects.get(email=username)
        except Identity.DoesNotExist:
            logger.info("Unknown identity login", extra={'username': username})
        else:
            if user.check_password(password):
                logger.info("User's password successfully checked", extra={'user': user})
                return user

            logger.info("backend's authenticate() failed")

    def get_user(self, user_id):
        """
        @param user_id: Identity's pk
        @type user_id: int
        @return: Identity matching pk given on input
        @rtype: Identity
        """
        try:
            return Identity.objects.get(pk=user_id)
        except Identity.DoesNotExist:
            logger.info("Unknown get_user id", extra={'user_id': user_id})
