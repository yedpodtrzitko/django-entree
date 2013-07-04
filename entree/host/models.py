from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from entree.host.managers import EntreeSiteManager

from cache_tools.fields import CachedForeignKey
from entree.host.profiles.managers import SiteProfileManager


ENTREE = settings.ENTREE


class EntreeSite(models.Model):
    title = models.CharField("Site title", max_length=100)
    url = models.URLField("Site url", max_length=150)
    is_active = models.BooleanField(_("active"), default=True, help_text=
                _("Designates whether this site should be treated as active."))
    secret = models.CharField(_("Site secret key"), max_length=40)
    is_default = models.NullBooleanField(_("is default site"), unique=True)

    objects = EntreeSiteManager()

    def __unicode__(self):
        return "Site %s" % self.title


class SiteProfile(models.Model):
    user = CachedForeignKey('enauth.Identity')
    site = CachedForeignKey("host.EntreeSite")
    is_active = models.BooleanField(_("Is active"), default=False)

    objects = SiteProfileManager()

    class Meta:
        unique_together = (
            ('user', 'site'),
        )

    def __unicode__(self):
        return u"<SiteProfile: %s at %s>" % (self.user, self.site)

