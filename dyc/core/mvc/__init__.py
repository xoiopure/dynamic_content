from .config import Config, DefaultConfig, model
from . import _pathmapper, controller
from .decorator import Autoconf, controller_function, controller_method, controller_class

del _pathmapper

__author__ = 'justusadam'


__all__ = [
    'Autoconf',
    'controller_method',
    'controller_function',
    'controller',
    'Config',
    'DefaultConfig',
    'controller_class'
    ]