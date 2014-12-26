import collections
import re
from dynct.errors import exceptions
from dynct.util import decorators
from .. import _component


__author__ = 'justusadam'


_register_controllers = True


@decorators.deprecated
class Controller(dict):
    pass


@_component.Component('ControllerMapping')
class ControllerMapper(dict):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._controller_classes = []
        self.register_modules()

    def register_modules(self):
        self.modules = _component.get_component('Modules')

    def sort(self):
        """
        Sorts all controller functions such that:
          1. functions with a specified regex will be preferred over those with None (or '')
          2. functions with longer regex will be preferred over shorter ones
          3. functions that accept no query or only specific keys will be preferred over
           those that accept any.

        This should in theory ensure, that more specific 'paths' are preferred over generic ones.
        """
        for item in self.values():
            # TODO check if this works correctly
            item.sort(key=lambda a: int(a.get is True) + int(a.post is True))
            item.sort(key=lambda a: len(a.orig_pattern) if a.orig_pattern else 0, reverse=True)

    def add_controller(self, prefix, function):
        self.setdefault(prefix, list()).append(function)


    def __call__(self, model, url):
        l = str(url.path).split('/', 2)
        if not l[0] == '' or len(l) < 2: raise AttributeError
        prefix = l[1]
        path = '/' + l[2] if len(l) > 2 else ''
        elements = self[prefix]
        for element in elements:
            if element.regex:
                m = re.fullmatch(element.regex, path)
                if not m:
                    continue
                else:
                    args = m.groups()
            else:
                args = (url, )
            try:
                get, post = element.get(url.get_query), element.post(url.post)
                result = element(model, *args, **dict(collections.ChainMap(get, post)))
                if not result:
                    continue
                else:
                    return result
            # except (PermissionError, TypeError) as e:
            except exceptions.UnexpectedControllerArgumentError:
                pass
        return 'error'