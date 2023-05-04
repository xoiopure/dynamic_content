"""Modelling of requests in special python classes"""
from urllib import parse
from . import headers as h_mod
import inspect

__author__ = 'Justus Adam'
__version__ = '0.1.1'


class Request(object):
    """
    Representation of a request with all important values and parameters
    """
    __slots__ = (
        'path',
        'headers',
        'query',
        'method',
        'client',
        'ssl_enabled',
        'host',
        'port',
        'payload'
    )

    def __init__(self, host, port, path:str, method, query, headers, ssl_enabled, payload):
        self.host = host
        self.port = port
        headers = h_mod.Header.auto_construct(headers) if headers is not None else None
        if inspect.isgenerator(headers):
            headers = h_mod.HeaderMap(headers)
        elif headers is None:
            headers = h_mod.HeaderMap()
        else:
            headers, header = h_mod.HeaderMap(), headers
            headers.add(header)
        self.headers = headers
        self.path = path
        self.method = method.lower()
        self.query = query
        self.client = None
        self.ssl_enabled = ssl_enabled
        self.payload = payload

    def parent_page(self):
        """
        Convenience method for generating a url of a parent page
        :return:
        """
        parent = self.path.rsplit('/', 1)
        return '/' if not parent or parent[0] == '' else parent[0]

    @classmethod
    def from_path_and_post(
            cls,
            host: str,
            path,
            method,
            headers,
            ssl_enabled: bool,
            query_string=None,
            payload=None
        ):
        """
        Construct a new Request object from alternative input

        :param host: host[:port] string
        :param path: path/to/resource
        :param method: request method (POST, GET)
        :param headers: request headers
        :param ssl_enabled: boolean to indicate http or https
        :param query_string: ?query=values&so_on
        :return: Request() instance modelling the request
        """
        host = host.rsplit(':', 1)
        port = int(host[1]) if len(host) == 2 else None
        host = host[0]
        parsed = parse.urlsplit(path)
        query = parse.parse_qs(parsed.query)
        if query_string:
            query.update(parse.parse_qs(query_string))
        path = parsed.path
        return cls(host, port, path, method, query, headers, ssl_enabled, payload)
