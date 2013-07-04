from app_data import app_registry

from entree.enauth.containers import EntreeDataContainer
from entree.enauth.models import LoginToken

app_registry.register('entree', EntreeDataContainer, LoginToken)
