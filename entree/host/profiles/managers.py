from cache_tools.utils import get_cached_object

from django.db import models
from django.conf import settings
from django.core.cache import cache


NOSITE_ID = settings.ENTREE['NOSITE_ID']


class SiteProfileManager(models.Manager):
    #TODO move into ProfileData
    def get_data(self, user, site=None, cascade=True, override_inactive=False):
        """
        cascade - obtain resident data as well
        override_inactive - obtain data even if profile is not active
        """
        from entree.host.models import EntreeSite

        site = site or get_cached_object(EntreeSite, pk=NOSITE_ID)

        profile, created = self.get_or_create(
            user=user, site=site,
            defaults={'is_active': False})

        if not profile.is_active and not override_inactive:
            return {'is_active': False}

        #obtain resident profile's data?
        if cascade and site.pk != NOSITE_ID:
            generic_data = self.get_data(override_inactive=True, user=user)
        else:
            generic_data = {}

        site_data = self.get_cached(dict(user=user, site=site))
        site_data['is_active'] = profile.is_active
        generic_data.update(site_data)

        return generic_data

    def get_cached(self, key, recache=True):
        """

        @param key: dict with models (user, site) to define cache key
        @type key: dict

        @return: cached data for SiteProfile
        @rtype: dict
        """
        hash_key = "%s:%s" % (key['user'].pk, key['site'].pk)
        data = cache.get(hash_key)
        if data is None or recache:
            from entree.host.profiles.models import ProfileData, ProfileDataUnique, SiteProperty

            props = SiteProperty.objects.get_site_props(site=key['site'], cascade=False)

            data_items = list(ProfileData.objects.filter(site_property__in=props, user=key['user'])) + \
                         list(ProfileDataUnique.objects.filter(site_property__in=props, user=key['user']))

            data = {}
            for one in data_items:
                data[one.site_property.slug] = one.value

            for one in props:
                if one.slug not in data:
                    data[one.slug] = ""

            cache.set(hash_key, data)
        return data
