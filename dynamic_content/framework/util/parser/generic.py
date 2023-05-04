import collections


__author__ = 'Justus Adam'
__version__ = '0.1'


class Edge(object):

    __slots__ = ('g', 'head', 'tail', 'chars', 'funcs')

    def __init__(self, head, tail, g=None, chars=set(), funcs=set()):
        self.head = head
        self.tail = tail
        self.g = g
        self.chars = {chars} if isinstance(chars, str) else set(chars)
        self.funcs = {funcs} if callable(funcs) else set(funcs)


EdgeFunc = collections.namedtuple('EdgeFunc', ('func', 'result'))


class Vertex(object):

    __slots__ = ('inner', 'f')

    def __init__(self, *edges):
        self.inner = {}
        self.f = set()
        for edge in edges:
            self.add_edge(edge)

    def add_edge(self, edge):
        for arg in edge.chars:
            if not isinstance(arg, str):
                raise TypeError(f'Expected type {str} or {callable}, got {type(arg)}')
            if arg in self.inner:
                raise SyntaxError(f'Edge to {arg} already exists')
            self.inner[arg] = edge
        for f in edge.funcs:
            if callable(f):
                self.f.add(EdgeFunc(func=f, result=edge))
            else:
                raise TypeError(f'Expected type {callable}, got {type(f)}')

    def match(self, character):
        if character in self.inner:
            return self.inner[character]
        for f in self.f:
            if f.func(character):
                return f.result


def _parse_deterministic(automaton, stack, string):

    linecount = 1
    charcount = 0

    node = automaton[0]

    for n in string:
        try:
            res = node.match(n)
            if res is None:
                raise SyntaxError(f'No Node found matching \nstack = \n{stack} \nand n = {n}')
            fres = res.g(n, stack) if res.g is not None else None
        except (KeyError, SyntaxError) as e:
            raise SyntaxError(
                f'On line {linecount} column {charcount}, nested exception {e}'
            )
        if res is None:
            raise SyntaxError(
                f'On line {linecount} column: {charcount} \nExpected characterfrom {node.inner.keys()} or conforming to {{f.func for f in node.f}}'
            )
        try:
            node = automaton[res.head if fres is None else fres]
        except KeyError:
            raise SyntaxError(f'No state {res.head} found in Automaton')

        if n == '\n':
            linecount += 1
            charcount = 0
        else:
            charcount += 1

    return stack


def _parse_indeterministic(automaton, stack, string):
    raise NotImplementedError


def automaton_from_list(l):
    sorter = collections.defaultdict(list)
    for item in l:
        sorter[item.tail].append(item)
    return {
        k: Vertex(*v) for k, v in sorter.items()
    }


def parse(automaton, stack, string, automaton_type='deterministic'):
    return {
        'deterministic': _parse_deterministic,
        'indeterministic': _parse_indeterministic
    }[automaton_type](automaton, stack, string)
