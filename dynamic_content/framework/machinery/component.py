"""
Implementation for globally available 'Singletons'
"""
import functools
from framework.errors import exceptions
from framework import util


__author__ = 'Justus Adam'
__version__ = '0.2.1'


def _name_transform(name):
    new_name = name.lower().replace('_', '').replace(' ', '')
    if not new_name.isalpha():
        raise ValueError(f'Bad character in {new_name}')
    return new_name


class ComponentWrapper(util.Maybe):
    """
    A Proxy object for components to allow modules to bind
     components to local variables before the component as been registered

    This means that if a non-existent component is being requested there
     will be no error only using the component will throw the
     ComponentNotLoaded exception.

    Please note that _name and _allow_reload can ONLY be set at instantiation.
    """

    __slots__ = 'name', 'allow_reload'

    def __init__(self, name, allow_reload=False, wrapped=None):
        super().__init__(wrapped)
        self.allow_reload = allow_reload
        self.name = name

    def set(self, obj):
        if not self.allow_reload and self.content is not None:
            raise exceptions.ComponentLoaded(self.name)
        self.content = obj

    def get(self):
        if self.content is None:
            raise exceptions.ComponentNotLoaded(self.name)
        return super().get()

    @property
    def wrapped(self):
        return self.get()


class ComponentContainer(dict):
    """
    Register Object for components.

    Dictionary with some special properties.

    Keys have to be strings or types and in the case of strings,
     are transformed into all lower case and spaces and underscores are removed.

    => "_my Property" -> "myproperty"

    thus "_my Property" = "myproperty"

    """
    __slots__ = ()

    def __setitem__(self, key, value):
        if isinstance(key, str):
            key = _name_transform(key)
        elif not isinstance(key, type):
            raise TypeError(f'Expected Type {str} or {type}, got {type(key)}')
        item = super().setdefault(key, ComponentWrapper(key))
        item.set(value)

    def __getitem__(self, key):
        if isinstance(key, type):
            return self.setdefault(key, ComponentWrapper(key))
        new_key = _name_transform(key)
        return super().setdefault(new_key, ComponentWrapper(new_key))

    __call__ = __getitem__

    def __getattr__(self, item):
        return self.__getitem__(item)

    def __contains__(self, item):
        return not (
            not super().__contains__(item)
            or self[item].get() is None
        )


# the only real singleton in the framework
call_component = get_component = component_container = ComponentContainer()


# removing the constructor for the accessor object
del ComponentContainer


def _decorator(name, args=None, kwargs=None):
    def inner(class_):
        if args is None and kwargs is None:
            obj = class_()
        elif args is None:
            obj = class_(**kwargs)
        elif kwargs is None:
            obj = class_(*args)
        else:
            obj = class_(*args, **kwargs)
        register(name, obj)
        if class_ not in component_container:
            register(class_, obj)
        return class_

    return inner


# some convenient decorators for registering components
Component = component = _decorator

del _decorator


def register(name, obj):
    """
    Register component in container

    :param name: component name
    :param obj: component instance
    :return: None
    """
    get_component[name].set(obj)


def inject(*components, **kwcomponents):
    """
    Injects components into the function.

    All *components will be prepended to the *args the
     function is being called with.

    All **kwcomponents will be added to (and overwrite on key collision)
     the **kwargs the function is being called with.

    :param components: positional components to inject
    :param kwcomponents: keyword components to inject
    :return:
    """

    components = tuple(get_component(a) for a in components)
    kwcomponents = {
        a: get_component(b) for a, b in kwcomponents.items()
    }

    def inner(func):
        """
        Inner function to allow call arguments

        :param func: function to wrap
        :return: function wrapper
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(
                *tuple(a.get() for a in components) + args,
                **dict(((a, b.get()) for a, b in kwcomponents.items()), **kwargs)
            )

        return wrapper

    return inner


def inject_method(*components, **kwcomponents):
    """
    Injects components into the function.

    All *components will be prepended to the *args the
     function is being called with.

    All **kwcomponents will be added to (and overwrite on key collision)
     the **kwargs the function is being called with.

    :param components: positional components to inject
    :param kwcomponents: keyword components to inject
    :return:
    """

    components = tuple(get_component(a) for a in components)
    kwcomponents = {
        a: get_component(b) for a, b in kwcomponents.items()
    }

    def inner(func):
        """
        Inner function
        :param func: function to wrap
        :return:
        """
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            """
            Wrapper function

            :param self: method typical self parameter
            :param args: call args
            :param kwargs: call kwargs
            :return: wrapped function call result
            """

            return func(
                *(self, ) + tuple(a.get() for a in components) + args,
                **dict(((a, b.get()) for a, b in kwcomponents.items()), **kwargs)
            )

        return wrapper

    return inner
