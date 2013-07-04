import logging

from app_data.fields import AppDataField

from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from entree.user.managers import EntreeUserDBManager


ENTREE = settings.ENTREE
logger = logging.getLogger(__name__)


class EntreeDBUser(AbstractBaseUser):
    key = models.CharField("Auth key", max_length=40, db_index=True, unique=True)
    username = models.CharField("Username", max_length=60, db_index=True, unique=True)
    email = models.EmailField(_('email address'), blank=True)
    is_staff = models.BooleanField(_('staff status'), default=False)
    is_superuser = models.BooleanField(_('superuser status'), default=False)
    is_active = models.BooleanField(_('active'), default=True)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    app_data = AppDataField()

    objects = EntreeUserDBManager()

    USERNAME_FIELD = 'username'

    def get_and_delete_messages(self):
        return []

    def __eq__(self, other):
        return self.key == other.key

    def __unicode__(self):
        return u'EntreeUser %s' % self.email
