import collections
import functools


__author__ = 'Justus Adam'
__version__ = '0.1'


# elements not closing
# <meta ... >
non_closing = {'meta', 'input', 'doctype'}

# elements definately closing
# <div ...> ... </div>
closing = {'div', 'html', 'span'}

# elements optionally closing
# <style ... > ... </style>
# or
# <style ... />
optional_closing = {'style'}

# elements always closing in short form
# <input ... />
short_closing = {'input'}

#
keep_formatting = {'code', 'pre'}


def unwrap_list(l):
    if isinstance(l, str):
        return l
    elif hasattr(l, '__iter__'):
        return ', '.join(l)
    else:
        raise TypeError


class Base(object):

    __slots__ = (
        '_children',
        '_value_params',
        '_params',
        'tag'
    )

    def __init__(self, tag, *children, **params):
        self.tag = tag
        self._children = list(children)
        self._params = set()
        self._value_params = {}
        for k, v in params:
            if isinstance(v, bool):
                self._params.add(k)
            else:
                self._value_params[k] = v

    @property
    def value_params(self):
        return self._value_params

    @property
    def params(self):
        return self._params

    def __getattr__(self, k):
        return self._value_params[k] if k in self._value_params else k in self._params

    def __setattr__(self, k, v):
        if k in self.__slots__:
            super().__setattr__(k, v)
        elif isinstance(v, bool):
            self._params.add(k)
        else:
            self._value_params[k] = v

    def children(self):
        return tuple(filter(lambda a: isinstance(a, Base), self._children))

    def text_fields(self):
        return tuple(filter(lambda a: isinstance(a, str), self._children))

    def text(self):
        return ''.join(self.text_fields())

    def render_tag(self):
        return self.tag

    def render(self):

        inner_head = ' '.join(
            (self.render_tag(),)
            + tuple(self._params)
            + tuple(
                f'{k}="{unwrap_list(v)}"'
                for k, v in self._value_params.items()
                if v is not None
            )
        )
        if self._children:
            return ''.join(('<', inner_head, '>',
                ''.join(a if isinstance(a, str) else a.render() for a in self._children),
                '</', self.tag,'>'))
        elif self.tag in non_closing:
            return f'<{inner_head}>'
        else:
            return f'<{inner_head} />'

    def __str__(self):
        return self.render()

    def append(self, child):
        self._children.append(child)

    def prepend(self, child):
        if not isinstance(self._children, collections.deque):
            self._children = collections.deque(self._children)

    def insert(self, index, element):
        self._children.insert(index, element)

    def content(self):
        return self._children

    def add_class(self, *classes):
        self._value_params.setdefault('class', set())
        for c in classes:
            self._value_params['class'].add(c)

    def _satisfies(self, *selectors, **vselectors):
        for selector in selectors:
            if selector not in self._params:
                return False
        return all(self._value_params[k] == v for k, v in vselectors.items())


    def _find(self, *selectors, **vselectors):
        try:
            if self._satisfies(*selectors, **vselectors):
                yield self
        except KeyError:
            None
        for child in self.children():
            yield from child._find(*selectors, **vselectors)

    def find(self, *selectors, **vselectors):
        return tuple(self._find(*selectors, **vselectors))


class Doctype(Base):
    def render_tag(self):
        return f'!{self.tag.upper()}'


class HTML(Base):
    __slots__ = (
        '_children',
        '_value_params',
        '_params',
        'tag',
        'doctype'
    )

    def __init__(self, tag, *children, **params):
        super().__init__(tag, *children, **params)
        self.doctype = None

    def render(self):
        if self.doctype:
            return self.doctype.render() + super().render()
        else:
            return f'<!DOCTYPE html>{super().render()}'


class _Hack(dict):
    def __getitem__(self, item):
        if item in self:
            return super().__getitem__(item)
        else:
            return functools.partial(Base, item)


_by_tag = {
    'html': HTML,
    'doctype': Doctype
}


by_tag = lambda tag: _by_tag.get(tag, Base)(tag)
