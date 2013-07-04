from django.conf import settings

if 'entree.client.db' in settings.INSTALLED_APPS:
    if 'entree.client.cached' in settings.INSTALLED_APPS:
        raise Exception("You can use only one entree.client app (db or cached)")
