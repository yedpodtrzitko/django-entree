import logging

from django.db import models


logger = logging.getLogger(__name__)


class IdentityManager(models.Manager):
    def create(self, **kwargs):
        """
        Creates a new object with the given kwargs, saving it to the database
        and returning the created object.
        """
        pwd = kwargs.pop('password', None)
        obj = self.model(**kwargs)
        obj.set_password(pwd)
        obj.save(using=self.db)
        return obj
