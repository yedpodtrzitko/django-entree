import logging

from django.conf import settings
from django.core.cache import cache
from django.db import models

from cache_tools.utils import get_cached_object


logger = logging.getLogger(__name__)
NOSITE_ID = settings.ENTREE['NOSITE_ID']


class EntreeSiteManager(models.Manager):
    def active(self):
        return self.get_query_set().filter(is_active=True).exclude(pk=NOSITE_ID)


class SitePropertyManager(models.Manager):
    def get_site_props(self, site=None, cascade=True):
        """
        @type site:  EntreeSite
        @param site: Site which attributes belongs to
        @type cascade:  boolean
        @param cascade: get also resident attributes (don't belong to any specific site)

        @rtype list
        @return list of SiteProperty items according to site_id given on input
        """
        from entree.host.models import EntreeSite

        site = site or get_cached_object(EntreeSite, pk=NOSITE_ID)

        if cascade and site.pk != NOSITE_ID:
            resident_props = self.get_site_props(cascade=False)
        else:
            resident_props = []

        site_props = self.get_data(site.pk)
        return site_props + resident_props

    def get_data(self, key):
        data = cache.get('siteprops:%s' % key)
        if data is None:
            data = list(self.get_query_set().filter(site_id=key))
            cache.set(key, data)
        return data
