"""
Modelling of headers in special python classes
for easier interaction with headers and values of headers
"""
import inspect

__author__ = 'Justus Adam'
__version__ = '0.1'


class Header:
    """Object representing a http header"""
    __slots__ = 'key', 'value'

    def __init__(self, key, value=None):
        self.key = key
        self.value = value

    @classmethod
    def from_str(cls, string:str):
        """
        Create a new Header Instance from an input string

        :param string:
        :return:
        """
        assert isinstance(string, str)
        k, v = string.split(': ', 1)
        return cls(k, v)

    @classmethod
    def many_from_str(cls, string:str):
        """
        Construct headers from an input string

        :param string:
        :return:
        """
        assert isinstance(string, str)
        for i in string.split('\r\n'):
            for s in i.split('\n'):
                yield cls.from_str(s)

    @classmethod
    def any_from_str(cls, string:str):
        """
        Construct many or one headers from string

        :param string:
        :return: Header or generator[Header]
        """
        assert isinstance(string, str)
        l = string.split('\n')
        return cls.from_str(l[0]) if len(l) == 1 else cls.many_from_str(string)

    @classmethod
    def many_from_dict(cls, d:dict):
        """
        Return iterable of Headers constructed from the dict
        :param d: dictionary
        :return: generator
        """
        assert isinstance(d, dict)
        for k, v in d.items():
            if isinstance(v, cls):
                yield v
            else:
                yield cls(k, v)

    @classmethod
    def from_tuple(cls, t):
        """
        Build new Header instance from a key, value tuple/list
        :param t: tuple/list
        :return: new Header
        """
        assert isinstance(t, (tuple, list))
        if len(t) == 2:
            return t[1] if isinstance(t[1], cls) else cls(*t)
        else:
            raise TypeError(
                f'tuple for header construction must have length 2, had length {len(t)}'
            )

    from_list = from_tuple

    @classmethod
    def many_from_tuple(cls, t):
        """
        Yield new Header instances from the tuple/list

        :param t: tuple/list
        :return: generator
        """
        assert isinstance(t, (tuple, list))
        for i in t:
            yield cls.auto_construct(i)

    @classmethod
    def many_from_set(cls, s):
        """
        Construct headers from a set of input data
        :param s:
        :return:
        """
        assert isinstance(s, (set, frozenset))
        for i in s:
            yield cls.auto_construct(i)

    many_from_list = many_from_tuple

    @classmethod
    def any_from_tuple(cls, t):
        """
        Build new Header instances from a tuple.

        If the tuple is ov type (key, value) only a
         single Header instance is returned

        Otherwise an iterable of new Headers is returned.

        :param t: tuple/list
        :return: generator or Header
        """
        assert isinstance(t, (tuple, list))
        if len(t) != 2 or not isinstance(t[0], str):
            return cls.many_from_tuple(t)
        try:
            return cls.from_str(t[0]), cls.from_str(t[1])
        except ValueError:
            return cls.from_tuple(t)

    any_from_list = any_from_tuple

    @classmethod
    def auto_construct(cls, raw):
        """
        Constructs a new Header instance with the appropriate classmethod
         determined by the type of the input
        :param raw: raw input data
        :return:
        """
        if isinstance(raw, cls):
            return raw
        elif isinstance(raw, dict):
            return cls.many_from_dict(raw)
        elif isinstance(raw, str):
            return cls.any_from_str(raw)
        elif isinstance(raw, (list, tuple)):
            return cls.any_from_tuple(raw)
        elif isinstance(raw, (set, frozenset)):
            return cls.many_from_set(raw)
        else:
            raise TypeError(f'The type {type(raw)} is not supported for auto construction')

    def to_tuple(self):
        """
        Return header values as a tuple

        :return:
        """
        return self.key, self.value

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.key == other.key and self.value == other.value
        else:
            return self == self.auto_construct(other)

    def __hash__(self):
        return (hash(self.key) << 1) ^ hash(self.value)

    equals = __eq__

    def __str__(self):
        return f'{str(self.key)}: {str(self.value)}'


class HeaderMap(dict):
    """
    Convenience dict for storing request related headers
    """
    __slots__ = ()

    def __init__(self, iterable=None, **kwargs):

        # ----------------------
        # begin helper methods
        # ----------------------

        def one(iterable):
            """
            helper method for header construction

            :param iterable:
            :return:
            """

            def convert(a):
                """
                transform input value to a header

                :param a:
                :return: (name, Header instance)
                """
                if not isinstance(a, Header):
                    a = Header.auto_construct(a)
                return a.key, a

            if iterable is not None:
                if isinstance(iterable, dict):
                    iterable = iterable.items()
                for i in iterable:
                    yield convert(i)
            for i in kwargs.items():
                yield convert(i)

        # ----------------------
        # end helper methods
        # ----------------------

        super().__init__(
            one(iterable)
        )

    def __setitem__(self, key, value):
        if not isinstance(value, Header):
            value = Header.from_tuple((key, value))
        super().__setitem__(key, value)

    def add(self, header):
        """
        Add a header or multiple to the dict
        :param header: input data
        :return: None
        """
        h = Header.auto_construct(header)
        if inspect.isgenerator(h):
            for i in h:
                self.add(i)
        else:
            self[h.key] = h

    def to_iter(self):
        """
        Return all values as an iterable of tuples

        :return: generator
        """
        for a in self.values():
            yield a.to_tuple()

    def to_tuple(self):
        """
        Return all values as a tuple of tuples

        :return: tuple
        """
        return tuple(self.to_iter())

    def to_set(self):
        """
        Return all values as a set of tuples

        :return: set
        """
        return set(self.to_iter())