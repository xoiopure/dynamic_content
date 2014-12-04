from .base import Commons
from . import model

__author__ = 'justusadam'


class TextCommons(Commons):
    com_type = 'text'

    def get_content(self, name):
        return model.CommonData.get(model.CommonData.machine_name==name).content