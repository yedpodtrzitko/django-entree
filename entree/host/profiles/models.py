from cache_tools.fields import CachedForeignKey

from django.db.models.signals import post_delete
from django.db import models, IntegrityError
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from entree.host.managers import SitePropertyManager


ENTREE = settings.ENTREE
TYPE_INT = 'integer'
TYPE_STR = 'string'
TYPE_BOOL = 'boolean'
PROPERTY_TYPE = (
    (TYPE_STR, _('string value (input)')),
    (TYPE_INT, _('integer value (input)')),
    (TYPE_BOOL, _('boolean value (checkbox)')),
)
PROPERTY_DEFAULT = TYPE_STR


class SiteProperty(models.Model):
    name = models.CharField(_("Property name"), max_length=50, help_text=_(
        "Property name as seen by user in his/her profile form"))
    slug = models.SlugField(_("Property slug"), max_length=50, help_text=_(
        "Text purposed to be used as a identify string for given property. "
        "It should be w/o spaces or some fancy chars, usually matches name."))
    site = CachedForeignKey("host.EntreeSite", blank=True, help_text=_(
        "Site to which property belongs to. Leave empty if it's supposed to be "
        "resident property for all sites"))
    value_type = models.CharField(_("Type of value"), max_length=10,
                                  default=PROPERTY_DEFAULT,
                                  choices=PROPERTY_TYPE, help_text=_(
            "Type of property's value; each type is represented by corresponding"
            " form input and may differs with its validation rules"
            " (ie. number vs. string)"))
    is_required = models.BooleanField(_("Property is required"), default=False)
    is_unique = models.BooleanField(_("Value is unique"), default=False,
                                    help_text=_("Each user should have unique value for this property (ie nickname)"))

    objects = SitePropertyManager()

    def __unicode__(self):
        return u"%s, site: %s" % (self.name, self.site)

    class Meta:
        unique_together = (
            ('slug', 'site'),
        )
        verbose_name_plural = _("Entree site properties")

    def save(self, *args, **kwargs):
        if self.site_id != ENTREE['NOSITE_ID']:
            resident_props = [one.slug for one in SiteProperty.objects.get_site_props()]
            if self.slug in resident_props:
                raise IntegrityError("Given attribute already exists as resident")
        super(SiteProperty, self).save(*args, **kwargs)


class ProfileDataBase(models.Model):
    """
    Store profiles data. Separate values enable easy searching for specific \
    property value (ie .'get users with newsletters')
    """

    user = CachedForeignKey('enauth.Identity')
    site_property = CachedForeignKey("host.SiteProperty")

    value_int = models.IntegerField(_("Integer property value"), null=True)
    value_str = models.CharField(_("Short string property value"), max_length=20, null=True)

    class Meta:
        abstract = True

    def __unicode__(self):
        return u"ProfileData %s" % self.site_property.name


class ProfileDataUnique(ProfileDataBase):

    class Meta:
        unique_together = (
            ('site_property', 'value_str'),
            ('site_property', 'value_int'),
        )

    def set_value(self, value, type_hint=None):
        """
        set value by its length into:
         `value` column (if length <= 20)
         `value_big` column (if length > 20)

        also if value is shorter but value_big already exists, \
        save it in there - it can happens again

        @param value: value to store
        @type value: mixed
        @return: None
        @rtype: None
        """
        self.value_str = None
        self.value_int = None

        type_hint = type_hint or self.site_property.value_type
        if type_hint == TYPE_INT:
            self.value_int = value
        else:
            self.value_str = value

        self.save()

    def get_value(self):
        return self.value_int or self.value_str

    value = property(get_value, set_value)


class ProfileBigData(models.Model):

    value = models.TextField(_("Property value"))


class ProfileData(ProfileDataBase):

    value_big = CachedForeignKey("host.ProfileBigData", null=True)
    value_bool = models.NullBooleanField(_("Boolean property value"))

    def set_value(self, value, type_hint=None):
        """
        set value by its length into:
         `value` column (if length <= 20)
         `big_value` column (if length > 20)

        also if value is shorter but big_value already exists, \
        save it in there - it can happens again

        @param value: value to store
        @type value: mixed
        @return: None
        @rtype: None
        """
        changed = True
        self.value_int = None
        self.value_str = None
        self.value_bool = None

        type_hint = type_hint or self.site_property.value_type
        if type_hint == TYPE_INT:
            self.value_int = value
        elif type_hint == TYPE_BOOL:
            self.value_bool = value
        else:
            if len(value) > 20 and not self.value_big:
                self.value_big = ProfileBigData.objects.create(value=value)
                self.value_str = None
            elif self.value_big:
                self.value_big.value = value
                self.value_big.save()
                changed = False
            else:
                self.value_str = value

        if not self.pk or changed:
            self.save()

    def get_value(self):
        if self.value_big:
            return self.value_big.value
        return self.value_int or self.value_bool or self.value_str

    value = property(get_value, set_value)


@receiver(post_delete, sender=SiteProperty)
def _signal_delete_profile_data(sender, **kwargs):
    prop = kwargs['instance']
    ProfileData.objects.filter(site_property=prop).delete()
    ProfileDataUnique.objects.filter(site_property=prop).delete()
