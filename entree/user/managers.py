import logging
import simplejson as json

from urllib2 import urlopen, URLError
from urllib import urlencode
from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, UNUSABLE_PASSWORD
from django.db import models

from entree.user.middleware import InvalidAuth
from entree.common.utils import COOKIE_CHECKSUM_SEPARATOR, calc_checksum, SHORT_CHECK

from cache_tools.utils import get_cached_object

ENTREE = settings.ENTREE
FETCH_TIMEOUT = 1  # seconds

logger = logging.getLogger(__name__)


class EntreeUserFetcherMixin(object):

    def fetch(self, raw_key):
        from entree.user.models import EntreeUser

        try:
            token, inner_checksum = raw_key.split(COOKIE_CHECKSUM_SEPARATOR)
        except ValueError:
            token = raw_key
        else:
            if inner_checksum != calc_checksum(token, length=SHORT_CHECK):
                raise InvalidAuth("Invalid cookie checksum")

        try:
            user = get_cached_object(EntreeUser, key=token)
        except EntreeUser.DoesNotExist:
            user = self.perform_fetch(token)

        return user

    def _fetch_params(self, token):
        checksum = calc_checksum("%s:%s" % (ENTREE['SITE_ID'], token), salt=ENTREE['SECRET_KEY'])
        return {
            'token': token,
            'checksum': checksum,
            'site_id': ENTREE['SITE_ID'],
        }

    def perform_fetch(self, token):
        from entree.user.models import EntreeUser

        url = "%s/%s" % (ENTREE['URL_SERVER'].rstrip('/'), ENTREE['ROUTE']['PROFILE_FETCH'].lstrip('/'))
        try:
            fp = urlopen(url, data=urlencode(self._fetch_params(token)), timeout=FETCH_TIMEOUT)
        except URLError, e:
            if getattr(e, 'code') == 403:
                raise InvalidAuth("Invalid token value")
            logger.error("Fetching remote profile failed")
            return AnonymousUser()

        try:
            json_data = json.load(fp)
        except json.JSONDecodeError:
            logger.error("Deserialization of remote profile failed")
            return AnonymousUser()
        else:
            #TODO - do a checksum of obtained data
            return EntreeUser.objects.create(key=token, data=json_data)


class EntreeUserDBManager(models.Manager, EntreeUserFetcherMixin):

    def create(self, key, **kwargs):
        """
        Creates and saves a EntreeUser with the given token key and params
        """
        now = datetime.now()
        user = self.model(key=key, username=kwargs['email'], email=kwargs['email'], is_staff=False,
                          is_active=True, is_superuser=False, date_joined=now)

        user.set_password(UNUSABLE_PASSWORD)
        user.save(using=self._db)
        return user
