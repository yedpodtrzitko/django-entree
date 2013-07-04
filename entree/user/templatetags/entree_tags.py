from django.template import Library
from entree.common.utils import SHORT_CHECK, calc_checksum

register = Library()

@register.filter
def enchecksum(text):
    return calc_checksum(text, length=SHORT_CHECK)
