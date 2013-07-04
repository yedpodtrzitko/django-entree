from hashlib import sha1
from django.conf import settings

ENTREE = settings.ENTREE
COOKIE_CHECKSUM_SEPARATOR = '|'
SHORT_CHECK = 10


def get_safe_entree():
    from copy import deepcopy

    PROTECTED_ITEMS = {
        'SECRET_KEY': "***"
    }

    protected = deepcopy(ENTREE)
    protected.update(PROTECTED_ITEMS)
    return protected


ENTREE_SAFE = get_safe_entree()


def calc_checksum(token, salt=None, length=40):
    salt = salt or ENTREE['SECRET_KEY']
    checksum = sha1(token + str(salt))
    return checksum.hexdigest().upper()[:length]
