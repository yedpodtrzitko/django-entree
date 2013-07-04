from django.conf import settings

if 'entree.user.db' in settings.INSTALLED_APPS:
    from entree.user.db.models import EntreeDBUser as EntreeUser
else:
    #from entree.client.cached.models import EntreeCacheUser as EntreeUser
    raise NotImplemented
