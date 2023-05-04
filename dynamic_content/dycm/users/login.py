import datetime
import logging
from http import cookies

from framework import http, hooks, route
from framework.util import html
from framework.middleware import csrf
from dycm import commons, theming
from . import session, users, decorator


__author__ = 'Justus Adam'

login_prefix = 'login'
logout_prefix = 'logout'

_cookie_time_format = '%a, %d %b %Y %H:%M:%S GMT'

USERNAME_INPUT = (
    html.Label('Username', label_for='username'),
    html.Input(name='username', required=True)
    )
PASSWORD_INPUT = (
    html.Label('Password', label_for='password'),
    html.Input(input_type='password', required=True,name='password')
    )

LOGOUT_TARGET = '/login'

LOGOUT_BUTTON = html.A(
    'Logout', href=f'/{logout_prefix}', classes={'logout', 'button'}
)


_login_failed = ':redirect:/login/failed'


class LoginHook(hooks.ClassHook):
    """
    A Hook designed to allow custom interaction with the login process.

    Usage:
     Alter the query using handle_form(form) by appending custom input fields.

     Handle part of the login POST request with handle_login_request(query)
      by returning according to the docstring in handle_login_request (query)
    """

    hook_name = 'login'

    def handle_form(self, form):
        """
        Alter the html form that is used for the login process.

        Append/prepend your custom input fields or return a new form

        Subsequent hooks will be called with your new form.

        :param form: csrf.SecureForm element
        :return: None or new csrf.SecureForm
        """
        raise NotImplementedError

    def handle_login_request(self, query):
        """
        Take action based on the query received with the login POST request

        If returning False will count request as failed.

        If returning True or None will continue.

        If returning 2-tuple will be interpreted as (username, password)
         and will immediately go onto opening the session,
         calling further hooks will be skipped

        If returning anything else will break and return that value.

        :param query: query dict object
        :return: any
        """
        raise NotImplementedError


LoginHook.init_hook()


def login_form():
    form = csrf.SecureForm(
        html.TableElement(USERNAME_INPUT, PASSWORD_INPUT),
        action=f'/{login_prefix}',
        classes={'login-form'},
        submit=html.SubmitButton(value='Login'),
    )
    for hook in LoginHook.get_hooks():
        res = hook.handle_form(form)
        if res is not None:
            form = res
    return form


LOGIN_COMMON = csrf.SecureForm(
    html.ContainerElement(*USERNAME_INPUT + PASSWORD_INPUT),
    action=f'/{login_prefix}',
    classes={'login-form'},
    submit=html.SubmitButton(value='Login'),
)


@commons.implements('login')
class LoginCommonHandler(commons.Handler):
    source_table = 'user_management'

    def get_content(self, conf, render_args, client):
        return LOGIN_COMMON


@route.controller_function(
    'login',
    method=http.RequestMethods.GET,
    query=False,
    require_ssl=True
    )
def login_(dc_obj):
    return login(dc_obj, None)


@route.controller_function(
    {'login/{str}'},
    method=http.RequestMethods.GET,
    require_ssl=True,
    query=False
    )
@decorator.authorize('access login page')
@theming.theme()
def login(dc_obj, failed):
    logging.getLogger(__name__).debug(failed)
    if failed == 'failed':
        message = html.ContainerElement(
            'Your Login failed, please try again.',
            classes={'alert'}
            )
    elif failed is None:
        message = ''
    else:
        return ':redirect:/login'
    dc_obj.context['content'] = html.ContainerElement(message, login_form())
    dc_obj.context['title'] = 'Login'
    return 'user_overview'


@route.controller_function(
    'login',
    method=http.RequestMethods.POST,
    query=True
    )
@decorator.authorize('access login page')
def login_post(dc_obj, query):
    for res in LoginHook.yield_call_hooks_with(
        lambda self, query: self.handle_login_request(query),
        query
    ):
        if res is False:
            return _login_failed
        if res is True:
            continue
        elif isinstance(res, (tuple, list)) and len(res) == 2:
            username, password = res
            break
        elif res is not None:
            return res
    else:
        if 'username' not in query or 'password' not in query:
            return
        username, password = query['username'], query['password']
        if len(username) != 1 or len(password) != 1:
            return ':redirect:/login/failed'
        username = username[0]
        password = password[0]
    try:
        token = session.start_session(username, password)
    except Exception:
        return _login_failed
    if token:
        cookie = cookies.SimpleCookie({'SESS': token})
        dc_obj.config['cookies'] = cookie
        return ':redirect:/'
    else:
        return _login_failed


@route.controller_function(
    'logout',
    method=http.RequestMethods.GET,
    query=True
    )
def logout(dc_obj, query):
    user = dc_obj.request.client.user
    if user == users.GUEST:
        return ':redirect:/login'
    session.close_session(user)
    time = datetime.datetime.utcnow() - datetime.timedelta(days=1)

    dest = query['destination'][0] if 'destination' in query else '/'
    dc_obj.config.setdefault(
        'cookies',
        cookies.SimpleCookie()).load({'SESS': ''}
        )
    dc_obj.config['cookies']['SESS']['expires'] = time.strftime(_cookie_time_format)
    return f':redirect:{dest}'
