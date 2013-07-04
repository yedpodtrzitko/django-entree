from cache_tools.utils import get_cached_object

from django.conf import settings
from django.contrib import admin
from django.forms import BaseInlineFormSet
from django.utils.translation import ugettext_lazy as _

from entree.host.models import EntreeSite
from entree.host.profiles.models import SiteProperty


class ResidentBlahFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        try:
            kwargs['instance'] = get_cached_object(EntreeSite, pk=settings.ENTREE['NOSITE_ID'])
        except EntreeSite.DoesNotExist:
            kwargs['instance'] = None
        super(ResidentBlahFormSet, self).__init__(*args, **kwargs)


class SitePropertiesAdmin(admin.TabularInline):
    model = SiteProperty
    prepopulated_fields = {"slug": ("name",)}

    verbose_name_plural = _("Site properties (available only for current site)")


class ResidentSitePropertiesAdmin(admin.TabularInline):
    model = SiteProperty
    #formset = ResidentBlahFormSet
    prepopulated_fields = {"slug": ("name",)}

    verbose_name_plural = _("Resident properties (applied to all sites)")
    verbose_name = _("Resident property (applies to all sites)")

    def get_formset(self, request, obj=None, **kwargs):
        try:
            obj = get_cached_object(EntreeSite, pk=settings.ENTREE['NOSITE_ID'])
        except EntreeSite.DoesNotExist:
            pass
        return super(ResidentSitePropertiesAdmin, self).get_formset(request, obj, **kwargs)


admin.site.register(SiteProperty, SitePropertiesAdmin)
