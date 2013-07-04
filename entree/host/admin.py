from django.db import models
from django.contrib import admin
from django.conf import settings
from django.forms import widgets

from entree.host.models import EntreeSite, SiteProfile


class EntreeSiteAdmin(admin.ModelAdmin):
    def __init__(self, *args, **kwargs):
        if 'entree.host.profiles' in settings.INSTALLED_APPS:
            from entree.host.profiles.admin import SitePropertiesAdmin, ResidentSitePropertiesAdmin
            self.inlines = [SitePropertiesAdmin, ResidentSitePropertiesAdmin]
        else:
            self.inlines = []
        return super(EntreeSiteAdmin, self).__init__(*args, **kwargs)

    formfield_overrides = {
        models.NullBooleanField: {'widget': widgets.CheckboxInput},
    }


class SiteProfileAdmin(admin.ModelAdmin):
    pass


admin.site.register(EntreeSite, EntreeSiteAdmin)
admin.site.register(SiteProfile, SiteProfileAdmin)
