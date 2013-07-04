from django import forms
from django.db import IntegrityError, transaction
from django.utils.translation import ugettext_lazy as _

from entree.host.models import SiteProfile


#TODO - highlight resident properties in form!
class ProfileForm(forms.Form):
    """
    Form for editing Identity's profile data.
    Handles also saving into DB, which is messy but it's ideal point for \
    handling IntegrityError, which we cannot get earlies
    """

    #if form has no props, show at least this checkbox
    dummy_is_activated = forms.BooleanField(label=_("Activated profile"))

    def __init__(self, user, site, *args, **kwargs):
        """
        - initialize fields according to actual site/user

        @param user: User to which profile belongs to
        @type user: Identity
        @param site: site to which profile belongs to
        @type site: EntreeSite
        @param args: default form's args
        @type args: list
        @param kwargs: default form's kwargs
        @type kwargs: dict
        """
        self.user = user
        self.site = site

        super(ProfileForm, self).__init__(*args, **kwargs)

        self._existing_data = None
        self._site_properties = None
        self.set_fields()

        self.fields['dummy_is_activated'].widget.attrs['readonly'] = True
        self.fields['dummy_is_activated'].widget.attrs['checked'] = True


    @property
    def site_properties(self):
        if self._site_properties is None:
            #TODO - get from cache
            site_props = SiteProperty.objects.get_site_props(site=self.site)
            self._site_properties = dict([(one.slug, one) for one in site_props])
        return self._site_properties

    def set_fields(self):
        profile_data = SiteProfile.objects.get_data(user=self.user, site=self.site, override_inactive=True)

        for key, one in self.site_properties.items():
            field_args = dict(
                label=one.name,
                initial=profile_data.get(one.slug, None),
                required=one.is_required
            )

            if one.value_type == 'boolean':
                field_instance = forms.BooleanField(**field_args)
            else:
                field_instance = forms.CharField(**field_args)

            self.fields[one.slug] = field_instance

    @transaction.commit_manually
    def clean(self):
        """
        Try to save data into DB.
        If we get some error, rollback and show form w/ errors

        @return: cleaned form's data
        @rtype: dict
        """
        data = self.cleaned_data

        for key, val in self.fields.items():
            try:
                self.upsert_item(key, data.get(key))
            except IntegrityError:
                self._errors[key] = self.error_class([unicode( _("Given value already taken by some other user, use different value.")) ])
                if key in self.cleaned_data:
                    del self.cleaned_data[key]
                transaction.rollback()

        profile, created = SiteProfile.objects.get_or_create(
            site=self.site,
            user=self.user,
            defaults={'is_active': True})

        if not profile.is_active:
            profile.is_active = True
            profile.save()
        elif not created:
            #updating, delete from cache
            #TODO - flush cache only
            SiteProfile.objects.get_cached(dict(user=profile.user, site=profile.site), recache=True)

        transaction.commit()

        return data

    @property
    def existing_data(self):
        """
        Load existing user's profile data for current site + resident data

        @return: user's data
        @rtype: dict
        """
        if self._existing_data is None:

            site_props_ids = [one.pk for one in self.site_properties.values()]

            tmp_data = list(ProfileData.objects.filter(site_property_id__in=site_props_ids, user=self.user).select_related('site_property')) +\
                       list(ProfileDataUnique.objects.filter(site_property_id__in=site_props_ids, user=self.user).select_related('site_property'))

            self._existing_data = dict([(one.site_property.slug, one) for one in tmp_data])
        return self._existing_data

    def upsert_item(self, key, value):
        """
        Save or update one item from form into DB.
        It can eventually raise IntegrityError

        @param key: slug of profile property
        @type key: str
        @param value: value of profile property
        @type value: str

        @raise IntegrityError
        """
        if key in 'dummy_is_activated':
            return

        site_prop = self.site_properties[key]
        if site_prop.is_unique:
            DataClass = ProfileDataUnique
        else:
            DataClass = ProfileData

        #site has property & property already exists - update
        if key in self.existing_data:
            self.existing_data[key].set_value(value, type_hint=site_prop.value_type)
        else:
            profile_data = DataClass(site_property=site_prop, user=self.user)
            profile_data.set_value(value)
