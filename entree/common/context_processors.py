from django.conf import settings

from entree.common.utils import ENTREE_SAFE


VARS = {
    'ENTREE': ENTREE_SAFE,
}


def common(request):
    if not getattr(settings, 'ENTREE', None):
        raise NotImplemented("""
        There's missing `ENTREE` directive in settings.
        Visit /api/show/<site_id>/ on your central authority to get it
        """)

    VARS.update({
        'entree_user': request.entree_user,
    })
    return VARS
