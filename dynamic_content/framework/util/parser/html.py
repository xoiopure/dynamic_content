from . import generic
from . import elements as _e


__author__ = 'Justus Adam'
__version__ = '0.1'


class ParserStack(object):
    __slots__ = (
        'element',
        'element_name',
        'argname',
        'kwarg_value',
        'text_content',
        'current'
    )

    def __init__(self,
        element = None,
        element_name = None,
        argname = None,
        kwarg_value = None,
        text_content = None,
        current = None
        ):
        self.element = element if element is not None else []
        self.element_name = element_name if element_name is not None else []
        self.argname = argname if argname is not None else []
        self.kwarg_value = kwarg_value if kwarg_value is not None else []
        self.text_content = text_content if text_content is not None else []
        self.current = current

    def __bool__(self):
        return (bool(self.element) and bool(self.element_name) and
            bool(self.argname) and bool(self.kwarg_value)
            and bool(self.text_content))

    def __str__(self):
        return f'element: {self.element}\nelement_name: {self.element_name}\nargname: {self.argname}\nkwarg_value: {self.kwarg_value}\ntext_content: {self.text_content}\ncurrent: {self.current}'


def flush_text_content(n, stack):
    if stack.text_content:
        if len(stack.text_content) != 1 or stack.text_content[0] != ' ':
            stack.current.append(''.join(stack.text_content))
        stack.text_content = []


def html_q2(n, stack):
    name = ''.join(stack.element_name).lower()
    element = _e.by_tag(name)

    stack.element.append(stack.current)
    stack.current = element
    stack.element_name = []


def html_q2_1(n, stack):
    html_q2(n, stack)
    finish_if_non_closing(n, stack)


def html_q4(n, stack):
    stack.current.params.add(''.join(stack.argname).lower())
    stack.argname = []


def html_q4_1(n, stack):
    html_q4(n, stack)
    finish_if_non_closing(n, stack)


def html_q6(n, stack):
    stack.current.value_params[''.join(stack.argname).lower()] = ''.join(stack.kwarg_value)
    stack.argname = []
    stack.kwarg_value = []


def html_q11(n, stack):
    name = ''.join(stack.element_name).lower()
    stack.element_name = []
    if stack.current.tag != name:
        raise SyntaxError(
            f'Mismatched closing tag. Expected {stack.current.tag}, found {name}'
        )
    html_finish_element(n, stack)


def html_finish_element(n, stack):
    parent = stack.element.pop()
    parent.append(stack.current)
    stack.current = parent


def finish_if_non_closing(n, stack):
    if stack.current.tag in _e.non_closing:
        html_finish_element(n, stack)


html_allowed = {'?', '!', '&', '%', '$'}


append_char = lambda n, stack: stack.text_content.append(n)
append_specific_char = lambda a: lambda n, stack: append_char(a, stack)
append_element_name = lambda n, stack: stack.element_name.append(n)
append_argname = lambda n, stack: stack.argname.append(n)

html_conform = lambda n: n.isalnum() or n in html_allowed


forbidden = {'"'}


# TODO add support for 'code' and 'pre'
automaton_base = (
    generic.Edge(1, 0, chars='<', g=flush_text_content),
    generic.Edge(0, 0, funcs=html_conform, g=append_char),
    generic.Edge(8, 0, chars={' ', '\n'}, g=append_specific_char(' ')),
    generic.Edge(2, 1, funcs=str.isalnum, g=append_element_name),
    generic.Edge(10, 1, chars='/'),
    generic.Edge(12, 1, chars='!'),
    generic.Edge(2, 2, funcs=str.isalnum, g=append_element_name),
    generic.Edge(0, 2, chars='>', g=html_q2_1),
    generic.Edge(3, 2, chars=' ', g=html_q2),
    generic.Edge(0, 3, chars='>', g=finish_if_non_closing),
    generic.Edge(4, 3, funcs=str.isalnum, g=append_argname),
    generic.Edge(9, 3, chars='/'),
    generic.Edge(3, 4, chars=' ', g=html_q4),
    generic.Edge(4, 4, funcs=str.isalnum, g=append_argname),
    generic.Edge(5, 4, chars='='),
    generic.Edge(0, 4, chars='>', g=html_q4_1),
    generic.Edge(6, 5, chars='"'),
    generic.Edge(
        6,
        6,
        funcs=lambda n: n not in forbidden,
        g=lambda n, stack: stack.kwarg_value.append(n),
    ),
    generic.Edge(7, 6, chars='"', g=html_q6),
    generic.Edge(0, 7, chars='>', g=finish_if_non_closing),
    generic.Edge(3, 7, chars=' '),
    generic.Edge(8, 8, chars={'\n', ' '}),
    generic.Edge(0, 8, funcs=html_conform, g=append_char),
    generic.Edge(1, 8, chars='<', g=flush_text_content),
    generic.Edge(0, 9, chars='>', g=html_finish_element),
    generic.Edge(11, 10, funcs=str.isalnum, g=append_element_name),
    generic.Edge(0, 11, chars='>', g=html_q11),
    generic.Edge(11, 11, funcs=str.isalnum, g=append_element_name),
    generic.Edge(13, 12, chars='-'),
    generic.Edge(1, 12, funcs=str.isalpha, g=append_element_name),
    generic.Edge(14, 13, chars='-', g=append_specific_char('<!--')),
    generic.Edge(14, 14, funcs=lambda a: True, g=append_char),
    generic.Edge(15, 14, chars='-'),
    generic.Edge(16, 15, chars='-'),
    generic.Edge(
        14,
        15,
        funcs=lambda a: True,
        g=lambda n, stack: stack.text_content.append(f'-{n}'),
    ),
    generic.Edge(0, 16, chars='>', g=append_specific_char('-->')),
    generic.Edge(
        14,
        16,
        funcs=lambda a: True,
        g=lambda n, stack: stack.text_content.append(f'--{n}'),
    ),
)

automaton = generic.automaton_from_list(automaton_base)


def parse(string):
    cellar_bottom = _e.Base('cellar')
    stack = ParserStack(current=cellar_bottom)
    stack = generic.parse(automaton, stack, string)
    if stack.current is not cellar_bottom:
        raise SyntaxError()
    c = list(cellar_bottom.content())
    if c[0].tag != 'doctype':
        return c
    if c[1].tag != 'html':
        raise TypeError
    c[1].doctype = c[0]
    return c[1:]
