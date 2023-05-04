"""Page elements displaying user information"""

from framework import route, http
from framework.util import html
from dycm import theming, commons
from dycm.users.login import LOGOUT_BUTTON
from dycm.users import users, decorator

__author__ = 'Justus Adam'


@commons.implements('user_information')
class UserInformationCommon(commons.Handler):
    source_table = 'user_management'

    def get_content(self, conf, render_args, client):
        return html.ContainerElement(
            html.ContainerElement(
                'Hello {}.'.format(' '.join(a for a in (
                    client.user.first_name,
                    client.user.middle_name,
                    client.user.last_name
                ) if a)),
                html_type='p'),
            html.TableElement(
                ('Your Username: ', self.get_username(client.user)),
                ('Your Access Group: ', client.access_group.machine_name),
                ('You Joined: ', self.get_date_joined(client.user))
            ),
            LOGOUT_BUTTON
        )

    @staticmethod
    def title(conf):
        return 'User Information'

    @staticmethod
    def get_username(user):
        return users.get_user(user).username

    @staticmethod
    def get_date_joined(user):
        if user == users.GUEST:
            return 'Not joined yet.'
        return users.get_user(user).date_created


@route.controller_function(
    'users/{int}',
    method=http.RequestMethods.GET,
    query=False
    )
@theming.theme(default_theme='admin_theme')
def user_information(dc_obj, uid):
    if not (
            (dc_obj.request.client.check_permission('view other user info') or
            dc_obj.request.client.check_permission('view own user'))
            if int(uid) == dc_obj.request.client.user
            else dc_obj.request.client.check_permission('view other user info')
    ):
        return 'error'

    dc_obj.context['title'] = 'User Information'

    user = users.get_single_user(int(uid))
    grp = user.access_group
    dc_obj.context['content'] = html.ContainerElement(
        html.TableElement(
            ('UID', str(user.oid)),
            ('Username', user.username),
            ('Email-Address', user.email_address),
            (
                'Full name',
                ' '.join((user.first_name, user.middle_name, user.last_name)),
            ),
            ('Account created', user.date_created),
            ('Access Group', f'{str(grp.oid)} ({grp.machine_name})'),
        )
    )
    return 'user_overview'


@route.controller_function('users', method=http.RequestMethods.GET, query=True)
@decorator.authorize('access users overview')
@theming.theme(default_theme='admin_theme')
def users_overview(dc_obj, get_query):

    selection = get_query['selection'][0] if 'selection' in get_query else '0,50'
    def all_users():
        for user in users.get_info(selection):
            href = '/users/{}'.format(user.oid)
            yield (
                html.A(str(user.oid), href=href),
                html.A(user.username, href=href),
                ' '.join((user.first_name, user.middle_name, user.last_name)),
                user.date_created,
                html.A('edit', href=f'/users/{str(user.oid)}/edit'),
            )

    user_list = tuple(all_users())

    head = (
        ('UID', 'Username', 'Name (if provided)', 'Date created', 'Actions')
        ,  # ...
    )
    dc_obj.context['title'] = 'User Overview'
    dc_obj.context['content']=(
        html.ContainerElement(
            html.TableElement(*head + user_list, classes={'user-overview'}),
            html.A('New User', href='/users/new', classes={'button'})
        )
        if user_list else
        html.ContainerElement(
            html.ContainerElement(
                'It seems you do not have any users yet.',
                additional={'style': 'padding:10px;text-align:center;'}
                ),
            html.ContainerElement(
                'Would you like to ',
                html.A(
                    'create one',
                    href='/users/new',
                    additional={
                        'style': 'color:rgb(255, 199, 37);text-decoration:none;'
                        }
                    ),
                '?',
                additional={'style': 'padding:10px;'}
                ),
            additional={
                'style': 'padding:15px; text-align:center;'
                    'background-color:cornflowerblue;'
                    'color:white;border-radius:20px;font-size:20px;'
                }
            )
        )
    return 'user_overview'
