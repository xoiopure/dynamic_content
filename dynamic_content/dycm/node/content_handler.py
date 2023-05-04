"""
Content creators of the node module

These are the classes exposed to the framework
"""

from datetime import datetime
import functools
import logging

from framework import http, route
from framework.machinery import component
from framework.util import lazy, html, clean
from dycm import wysiwyg
from dycm.commons import menus as _menus, model as commonsmodel
from dycm.users import decorator as user_dec

from . import model as _model, field
from .node import make_node


__author__ = 'Justus Adam'
__version__ = '0.2.1'


_access_modifier = 'access'
_edit_modifier = 'edit'
_add_modifier = 'add'

_publishing_flag = 'published'

_step = 5

_scroll_left = '<'
_scroll_right = '>'


@component.Component('CMSCompilers')
class Compilers(lazy.Loadable):
    """
    Component containing an instance of FieldBasedPageContent
    for each content type
    """
    def __init__(self):
        self._dict = None
        super().__init__()

    @lazy.ensure_loaded
    def __getitem__(self, item):
        if isinstance(item, _model.ContentType):
            item = item.machine_name
        return self._dict[item]

    def load(self):
        """
        Creates a FieldBasedPageContent instance for each content type
        and registers it
        """
        self._dict = {
            ct.machine_name: FieldBasedPageContent(ct)
            for ct in _model.ContentType.select()
            }


class FieldBasedPageContent(object):
    _editorial_list_base = edits = (('edit', _edit_modifier), )
    _view_name = 'page'
    page_type = 'node'

    def __init__(self, content_type):
        # we save the database representation
        self.dbobj = content_type

        # for conveniense the name of the content type again
        self.content_type = content_type.machine_name
        self.fields = list(self.get_fields())
        self.theme = self.dbobj.theme

    def get_permission(self, page, modifier):
        """
        Custom way for verifying a permission is granted
        """
        return self.join_permission(modifier) if page.published else \
            self.join_permission('access unpublished')

    def compile(self, dc_obj, page, modifier):

        def _(page):
            raise TypeError(modifier)

        mapped = {
            _access_modifier : self.field_contents,
            _edit_modifier : self.edit_form,
            _add_modifier : self.add_form
            }

        if not dc_obj.request.client.check_permission(
            self.get_permission(page, modifier)
            ):
            return None

        node = dict(
            editorial=self.editorial(page, dc_obj.request.client),
            content=mapped.get(modifier, _)(page),
            title=page.page_title
            )

        return node

    def field_contents(self, page):
        """
        The combined content of the page fields
        """
        return ''.join(str(a) for a in self.field_display(page))

    def field_display(self, page):
        """
        The page fields when just accessing the page

        :param page: the page value object
        :return: generator of field contents
        """
        f = lambda a: a['content']
        for single_field in self.fields:
            yield f(single_field.access(page))

    def field_edit(self, page):
        """
        The page fields when editing an existing page

        :param page: the page value object
        :return: generator of labels and fields
        """
        for single_field in self.fields:
            a = single_field.edit(page)
            yield html.Label(a['name'], label_for=a['name'])
            yield a['content']

    def field_add(self):
        """
        The Page fields when adding a new page
        """
        for single_field in self.fields:
            a = single_field.add()
            yield html.Label(a['name'], label_for=a['name'])
            yield a['content']

    def access(self, dc_obj, page):
        """
        the compiler function for page content access
        """
        return self.compile(dc_obj, page, _access_modifier)

    @wysiwyg.use()
    def edit(self, dc_obj, page):
        return self.compile(dc_obj, page, _edit_modifier)

    def process_edit_request(self, dc_obj, page, query):
        if not dc_obj.request.client.check_permission(
            self.get_permission(page, 'edit')
        ):
            return None
        try:
            success = self.do_edit(page, query)
        except Exception as e:
            logging.getLogger(__name__).warning(e)
            success = False

        return f":redirect:/node/{page.oid}{'' if success else '/add'}"

    def do_edit(self, page, query):
        for one_field in self.fields:
            one_field.process_edit_request(page.oid, query[one_field.name][0])
        page.page_title = clean.remove_dangerous_tags(query['title'][0])
        page.published = _publishing_flag in query
        page.menu_item = (
                None if query['parent-menu'][0] == 'none'
                else self.get_menu(*query['parent-menu'][0].rsplit('-', 1))
                )
        page.save()
        return True

    @wysiwyg.use()
    def add(self, dc_obj):
        return (
            dict(
                editorial='',
                content=self.add_form(),
                title=f'New {self.content_type} Page',
            )
            if dc_obj.request.client.check_permission(self.join_permission('add'))
            else None
        )

    def add_form(self):
        content = self.title_options() + tuple(self.field_add())
        return html.FormElement(
            *content + (self.admin_options(),),
            action=f'/node/add/{self.content_type}',
            classes={'edit', self.content_type, 'edit-form'},
        )

    def edit_form(self, page):
        content = self.title_options(page) + tuple(self.field_edit(page))
        return html.FormElement(
            *content + (self.admin_options(page),),
            action=f'/node/{str(page.oid)}/edit',
            classes={'edit', self.content_type, 'edit-form'},
        )

    def editorial(self, page, client):
        if l := self.editorial_list(page, client):
            return html.List(
                *[
                    html.A(
                        name,
                        href=link,
                        classes={'editorial-link'},
                    ) for name, link in l
                ],
                classes={'editorial-list'}
                )
        else:
            return ''

    def join_permission(self, modifier):
        return ' '.join([modifier, 'content type', self.content_type])

    def get_fields(self):
        field_info = _model.FieldConfig.select().where(
                        _model.FieldConfig.content_type == self.dbobj
                        )
        for a in field_info:
            yield field.Field(a, self.page_type)

    def editorial_list(self, page, client):
        for (name, modifier) in self._editorial_list_base:
            if client.check_permission(self.join_permission(modifier)):
                yield (
                    name,
                    '/'.join(['', self.page_type, str(page.oid), modifier])
                    )

    @staticmethod
    def get_menu(menu_name, item_id):
        item_id = int(item_id)
        return commonsmodel.MenuItem.get(
            menu=commonsmodel.Menu.get(machine_name=menu_name),
            oid=item_id
        )

    def process_add(self, query, client):
        page = _model.Page.create(
            content_type=self.dbobj,
            creator=client.user,
            page_title=clean.remove_dangerous_tags(query['title'][0]),
            published=_publishing_flag in query,
            date_created=datetime.now(),
            menu_item=(
                None if query['parent-menu'][0] == 'none'
                else self.get_menu(*query['parent-menu'][0].rsplit('-', 1))
                )
        )
        for field in self.fields:
            field.process_add(
                page_type=self.page_type,
                page_id=page.oid,
                content=query.get(field.name, [None])[0]
            )

        return f':redirect:/node/{page.oid}'

    @staticmethod
    def admin_options(page=None):
        if page is not None and page.menu_item is not None:
            parent = '-1' if page.menu_item is None else page.menu_item
            selected = f'{page.menu_item.menu.machine_name}-{parent}'
            m_c = _menus.menu_chooser('parent-menu', selected=selected)
        else:
            m_c = _menus.menu_chooser('parent-menu')
        menu_options = html.TableRow(
            html.Label(
                'Menu Parent',
                label_for='parent-menu'
                ),
            str(m_c),
            classes={'menu-parent'}
            )
        publishing_options = html.TableRow(
            html.Label('Published', label_for='toggle-published'),
            html.Checkbox(
                element_id='toggle-published',
                value=_publishing_flag,
                name=_publishing_flag,
                checked=False if page is None else page.published),
            classes={'toggle-published'}
            )

        return html.TableElement(
                    publishing_options,
                    menu_options,
                    classes={'admin-options'}
                    )

    @staticmethod
    def title_options(page=None):
        input_element = functools.partial(
            html.TextInput,
            element_id='edit-title',
            name='title',
            required=True,
            size=90
            )
        return (
            html.Label('Title', label_for='edit-title'),
            (
                input_element()
                if page is None
                else input_element(value=page.page_title)
            )
        )


@route.controller_class
class CMSController(object):

    @component.inject_method('CMSCompilers')
    def __init__(self, compiler_map):
        self.compiler_map = compiler_map

    @route.controller_method(
        {'/node/{int}', 'node/{int}/access'},
        method=http.RequestMethods.GET,
        query=False
        )
    @make_node()
    def handle_compile(self, dc_obj, page_id):
        page = _model.Page.get(oid=page_id)
        return self.compiler_map[page.content_type].access(dc_obj, page)


    @route.controller_method(
        '/node/{int}/edit',
        method=http.RequestMethods.POST,
        query=True
        )
    def handle_edit(self, dc_obj, page_id, post):
        page = _model.Page.get(oid=page_id)
        handler = self.compiler_map[page.content_type.machine_name]
        return handler.process_edit_request(dc_obj, page, post)


    @route.controller_method(
        '/node/{int}/edit',
        method=http.RequestMethods.GET,
        query=False
        )
    @make_node()
    def handle_edit_page(self, dc_obj, page_id):
        page = _model.Page.get(oid=page_id)
        handler = self.compiler_map[page.content_type.machine_name]
        return handler.edit(dc_obj, page)


    @route.controller_method(
        '/node',
        method=http.RequestMethods.GET,
        query=True
        )
    @user_dec.authorize('access node overview')
    @make_node()
    def overview(self, dc_obj, get):
        my_range = (
            int(get['from'][0]) if 'from' in get else 0,
            int(get['to'][0]) if 'to' in get else _step
        )
        for a in _model.Page
            .select()
            .limit(f'{my_range[0]},{my_range[1] - my_range[0] + 1}').order_by('date_created desc'):
            handler = self.compiler_map[a.content_type.machine_name]
            node = handler.access(dc_obj, a)
            if not node:
                continue
            node['title'] = html.A(node['title'], href=f'/node/{a.oid}')
            yield node

    @route.controller_method(
        '/node/add/{str}',
        method=http.RequestMethods.GET,
        query=False
        )
    @make_node()
    def add(self, dc_obj, content_type):
        handler = self.compiler_map[content_type]
        return handler.add(dc_obj)

    @route.controller_method(
        '/node/add/{str}',
        method=http.RequestMethods.POST,
        query=True
        )
    def process_add(self, dc_obj, content_type, query):
        handler = self.compiler_map[content_type]
        return handler.process_add(query, dc_obj.request.client)
