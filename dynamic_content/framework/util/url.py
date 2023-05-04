"""
Implementation of custom, object oriented tools for url parsing.

In part uses the standard library to parse and escape/unescape queries. Implementation might be subject to change in
the future, incorporate more of the standard library.
"""

from urllib import parse

__author__ = 'Justus Adam'


class Url:
    post = None

    def __init__(self, url, post=None):
        parsed = parse.urlsplit(url)
        self.method = 'get'
        self.path = parsed.path
        self.location = UrlLocation(parsed.fragment)
        self.query = (
            UrlQuery(post)
            if post is not None
            else UrlQuery(parsed.query, safe='/')
        )

    def __str__(self):
        return parse.urlunsplit(('', '', str(self.path), str(self.query), str(self.location)))

    def __bool__(self):
        return bool(self.path)


# class UrlPath:
#     def __init__(self, path):
#         self.path = path
#
#     @property
#     def path(self):
#         return self._path
#
#     @path.setter
#     def path(self, value):
#         self.trailing_slash = value.endswith('/') and len(value) > 1
#         self.starting_slash = value.startswith('/')
#         self._path = list(filter(lambda s: s is not '' and s is not None, parse.unquote_plus(value).split('/')))
#
#     def __str__(self):
#         return self.prt_to_str()
#
#     def prt_to_str(self, start=0, stop=0):
#         if stop == 0:
#             slc = self._path[start:]
#         else:
#             slc = self._path[start:stop]
#         acc = ''
#         if self.starting_slash:
#             acc += '/'
#         acc += '/'.join(slc)
#         if self.trailing_slash:
#             acc += '/'
#         return parse.quote(acc)
#
#
#     def __getitem__(self, item):
#         return self.path[item]
#
#     def __setitem__(self, key, value):
#         self._path[key] = value
#
#     def __len__(self):
#         return len(self.path)
#
#     def __contains__(self, item):
#         return item in self.path
#
#     def __bool__(self):
#         return bool(self.path)


class UrlLocation:
    def __init__(self, location):
        self.location = location

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value):
        if value.startswith('#'):
            value = value[1:]
        self._location = parse.unquote(value)

    def __str__(self):
        return f'#{parse.quote(self.location)}' if self._location else ''

    def __bool__(self):
        return bool(self.location)


class UrlQuery(dict):
    def __init__(self, query, safe=''):
        self.safe = safe
        if not query:
            super().__init__()
        elif isinstance(query, dict):
            super().__init__(**query)
        elif isinstance(query, str):
            super().__init__(**parse.parse_qs(query))

    def __str__(self):
        return parse.urlencode(self, doseq=True, safe=self.safe) if self else ''