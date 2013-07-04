from app_data import AppDataContainer
from entree.enauth.forms import EntreeDataForm


class EntreeDataContainer(AppDataContainer):
    form_class = EntreeDataForm
