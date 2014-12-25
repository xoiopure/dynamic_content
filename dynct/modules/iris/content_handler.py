from urllib import parse, error

from dynct import core
from dynct.core.mvc import content_compiler as _cc, decorator as mvc_dec, model as mvc_model
from dynct.modules.comp import decorator as comp_dec
from dynct.modules.comp import html
from dynct.modules.iris import node as _node
from dynct.modules import wysiwyg
from dynct.util import url as _url
from dynct.core import model as coremodel
from dynct.modules.commons import menus as _menus, model as commons_model
from . import model as _model, decorator


__author__ = 'justusadam'

_access_modifier = 'access'
_edit_modifier = 'edit'
_add_modifier = 'add'

_publishing_flag = 'published'

_step = 5

_scroll_left = '<'
_scroll_right = '>'



def not_over(a, val):
    if a > val:
        return val
    else:
        return a
def not_under(a, val=0):
    if a < val:
        return val
    else:
        return a


@core.Component('AccessIris')
class FieldBasedPageContent(object):
    modifier = _access_modifier
    _editorial_list_base = edits = [('edit', _edit_modifier)]

    def __init__(self):
        self.fields = self.get_fields()
        self.modules = core.Modules

    def __call__(self, model, url):
        page = self.get_page(url)
        self._theme = self.page.content_type.theme
        permission = self.join_permission(self.modifier, self.page.content_type)
        permission_for_unpublished = self.join_permission('access unpublished', self.page.content_type)

    def get_page(self, url):
        return _model.Page.get(_model.Page.oid==url.page_id)


    @staticmethod
    def join_permission(modifier, content_type):
        return ' '.join([modifier, 'content type', content_type])

    def get_fields(self):
        field_info = _model.FieldConfig.get_all(_model.FieldConfig.content_type==self.page.content_type)
        for a in field_info:
            yield self.get_field_handler(a.machine_name, a.handler_module)

    def handle_single_field_post(self, field_handler):
        query_keys = field_handler.get_post_query_keys()
        if query_keys:
            vals = {}
            for key in query_keys:
                if key in self.url.post:
                    vals[key] = self.url.post[key]
            if vals:
                field_handler.process_post(_url.UrlQuery(vals))

    def handle_single_field_get(self, field_handler):
        query_keys = field_handler.get_post_query_keys()
        if query_keys:
            vals = {}
            for key in query_keys:
                if key in self.url.get_query:
                    vals[key] = self.url.post[key]
            if vals:
                field_handler.process_get(_url.UrlQuery(vals))

    def get_field_handler(self, name, module):
        return self.modules[module].field_handler(name, self.url.page_type, self.url.page_id, self.modifier)

    def concatenate_content(self, fields):
        content = self.field_content(fields)
        return html.ContainerElement(*content)

    def field_content(self, fields):
        content = []
        for field in fields:
            content.append(field.compile().content)
        return content

    def process_content(self):
        return self.concatenate_content(self.fields)

    def editorial_list(self):
        for (name, modifier) in self._editorial_list_base:
            if self.check_permission(self.join_permission(modifier, self.page.content_type)):
                yield (name, '/'.join(['', self.url.page_type, str(self.url.page_id), modifier]))


class EditFieldBasedContent(FieldBasedPageContent):
    modifier = _edit_modifier
    _editorial_list_base = [('show', _access_modifier)]
    field_identifier_separator = '-'
    theme = 'admin_theme'

    def __init__(self, model, url):
        super().__init__(model, url)
        self.menu_item = commons_model.MenuItem.get_all(item_path=self.url.path.prt_to_str(0, -1))
        if self.menu_item:
            self.menu_item = self.menu_item[0]

    @property
    def page_title(self):
        return ' '.join([self.modifier, self.page.content_type, 'page'])

    @property
    def title_options(self):
        return [html.Label('Title', label_for='edit-title'),
                html.TextInput(element_id='edit-title', name='title', value=self.page.page_title, required=True, size=100)]

    def concatenate_content(self, fields):
        content = [self.title_options]
        content += self.field_content(fields)
        table = html.TableElement(*content, classes={'edit', self.page.content_type, 'edit-form'})
        return html.FormElement(table, self.admin_options(), action=str(self.url))

    def field_content(self, fields):
        for field in fields:
            identifier = self.make_field_identifier(field.machine_name)
            c_fragment = field.compile()
            c_fragment.content.classes.add(self.page.content_type)
            c_fragment.content.element_id = identifier
            yield html.Label(field.machine_name, label_for=identifier), str(c_fragment.content)

    def make_field_identifier(self, name):
        return self.modifier + self.field_identifier_separator + name

    def admin_options(self):
        if self.menu_item:
            parent = {False: self.menu_item.parent_item, True: str(-1)}[self.menu_item.parent_item is None]
            selected = '-'.join([self.menu_item.menu, str(parent)])
            m_c = _menus.menu_chooser('parent-menu', selected=selected)
        else:
            m_c = _menus.menu_chooser('parent-menu')
        menu_options = html.TableRow(
            html.Label('Menu Parent', label_for='parent-menu') , m_c, classes={'menu-parent'})
        publishing_options = html.TableRow(
            html.Label('Published', label_for='toggle-published'),
               html.Checkbox(element_id='toggle-published', value=_publishing_flag, name=_publishing_flag,
                        checked=self.published), classes={'toggle-published'})

        return html.TableElement(publishing_options, menu_options, classes={'admin-options'})

    def process_fields(self, fields):
        for field in fields:
            field.process_post()

    def assign_inputs(self, fields):
        for field in fields:
            field.query = {key: [parse.unquote_plus(a) for a in self.url.post[key]] for key in field.post_query_keys}

    def process_page(self):
        if not 'title' in self.url.post:
            raise ValueError
        self.page.page_title = parse.unquote_plus(self.url.post['title'][0])
        if _publishing_flag in self.url.post:
            published = True
        else:
            published = False
        self.page.published = published
        self.page.save()
        if 'parent-menu' in self.url.post:
            if self.url.post['parent-menu'][0] == 'none':
                if self.menu_item:
                    self.menu_item.delete()
            else:
                menu_name, parent = self.url.post['parent-menu'][0].split('-', 1)
                if parent == str(_menus.root_ident):
                    parent = None
                if self.menu_item:
                    self.menu_item.parent_item = parent
                    self.menu_item.menu = menu_name
                else:
                    self.menu_item = commons_model.MenuItem(self.page_title,
                                 self.url.path.prt_to_str(0,1) + '/' + str(self.url.page_id),
                                 menu_name,
                                 True,
                                 parent,
                                 10)
                self.menu_item.save()
        return self.url.path.prt_to_str(0,1) + '/' + str(self.url.page_id)

    def _process_post(self):
        self.assign_inputs(self.fields)
        try:
            page = self.process_page()
            self.process_fields(self.fields)
            self.redirect(page)
        except ValueError:
            pass

    def compile(self):
        if self.url.post:
            self._process_post()
        wysiwyg.decorator_hook(self._model)
        return super().compile()

    def redirect(self, destination=None):
        if 'destination' in self.url.get_query:
            destination = self.url.get_query['destination'][0]
        elif not destination:
            destination = str(self.url.path.prt_to_str(0, -1))
        raise error.HTTPError(str(self.url), 302, 'Redirect',
                        {('Location', destination), ('Connection', 'close')}, None)


class AddFieldBasedContentHandler(EditFieldBasedContent):
    modifier = 'add'

    def get_page(self):
        if 'ct' in self.url.get_query:
            content_type = self.url.get_query['ct'][0]
        elif len(self.url.path) == 3:
            content_type = self.url.path[2]
        else:
            raise TypeError
        display_name = coremodel.ContentTypes.get(content_type_name=content_type).display_name
        title = 'Add new ' + display_name + ' page'
        return _model.Page(content_type= content_type, title=title, creator=self.client.user)

    def process_page(self):
        self.page.page_title = parse.unquote_plus(self.url.post['title'][0])
        self.page.published = _publishing_flag in self.url.post
        self.page.save()
        page_id = self.page.get_id()
        self.update_field_page_id(page_id)
        self.url.page_id = page_id
        return self.url.path.prt_to_str(0,1) + '/' + str(self.url.page_id)

    def update_field_page_id(self, page_id):
        for field in self.fields:
            field.page_id = page_id

    @property
    def title_options(self):
        return [html.Label('Title', label_for='edit-title'), html.TextInput(element_id='edit-title', name='title', size=100, required=True)]


class Overview(_cc.Content):
    def __init__(self, model, url):
        super().__init__(model)
        self.url = url
        self.page_title = 'Overview'
        self.permission = ' '.join(['access', self.url.page_type, 'overview'])

    def get_range(self):
        return [
            int(self.url.get_query['from'][0]) if 'from' in self.url.get_query else 0,
            int(self.url.get_query['to'][0])   if 'to'   in self.url.get_query else _step
        ]

    def max(self):
        return _model.Page.select().order_by('id desc').limit(1).oid

    def scroll(self, range):
        acc = []
        if not range[0] <= 0:
            after = not_under(range[0] - 1, 0)
            before = not_under(range[0] - _step, 0)
            acc.append(html.A(''.join([str(self.url.path), '?from=', str(before), '&to=', str(after)]), _scroll_left, classes={'page-tabs'}))
        maximum = self.max()
        if not range[1] >= maximum:
            before = not_over(range[1] + 1, maximum)
            after = not_over(range[1] + _step, maximum)
            acc.append(html.A(''.join([str(self.url.path), '?from=', str(before), '&to=', str(after)]), _scroll_right, classes={'page-tabs'}))
        return html.ContainerElement(*acc)

    def process_content(self):
        range = self.get_range()
        def pages():
            for a in _model.Page.select().limit(','.join([str(a) for a in [range[0], range[1] - range[0] + 1]])).order_by( 'date_created desc'):
                u = _url.Url(str(self.url.path) + '/' + str(a.id))
                u.page_type = self.url.page_type
                u.page_id = str(a.id)
                m = mvc_model.Model()
                FieldBasedPageContent(m, u).compile()
                yield u, m
        content = [html.ContainerElement(html.A(str(a.path), html.ContainerElement(b['page_title'], html_type='h2')), html.ContainerElement(b['content'])) for a, b in pages()]
        content.append(self.scroll(range))
        return html.ContainerElement(*content)


@mvc_dec.controller_function('iris', '$', post=False)
@comp_dec.Regions
@decorator.node_process
def overview(page_model, get):
    page_model.client.check_permission(' '.join(['access', 'iris', 'overview']))
    my_range = [
            int(get['from'][0]) if 'from' in get else 0,
            int(get['to'][0])   if 'to'   in get else _step
        ]
    for a in _model.Page.select().limit(','.join([str(a) for a in [my_range[0], my_range[1] - my_range[0] + 1]])).order_by('date_created desc'):
        node = _node.access_node(page_model, 'iris', a.oid)
        node['title'] = html.A('/iris/' + str(a.oid), node['title'])
        yield node


@mvc_dec.controller_class
class IrisController:
    handler_map = {
        _access_modifier: FieldBasedPageContent,
        _edit_modifier: EditFieldBasedContent,
        _add_modifier: AddFieldBasedContentHandler,
    }

    @decorator.node_process
    def overview(self, model, url):
        return Overview(model, url).compile()

    @mvc_dec.controller_method('iris', '/([1-9]+)/edit', get=False, post=True)
    @decorator.node_process
    def edit(self, model, node_id, post):
        pass

    @mvc_dec.controller_method('iris')
    @comp_dec.Regions
    def handle(self, model, url, get, post):
        if len(url.path) == 3:
            if not url.path[1].isdigit():
                if url.path[1] == _add_modifier:
                    page_modifier = _add_modifier
                    url.page_id = 0
                else:
                    raise TypeError
            else:
                url.page_id = int(url.path[1])
                page_modifier = url.path[2]
        elif len(url.path) == 2:
            if url.path[1].isdigit():
                url.page_id = int(url.path[1])
                page_modifier = _access_modifier
            else:
                if not url.path[1] == _add_modifier:
                    raise TypeError
                page_modifier = _add_modifier
                # This is dirty and should not be done this way
                url.page_id = 0
        elif len(url.path) == 1:
            page_modifier = 'overview'
            url.page_type = url.path[0]
        else:
            raise TypeError
        url.page_type = url.path[0]
        return self.handler_map[page_modifier](model, url).compile()

@mvc_dec.controller_function('iris', '/([1-9]+)(?:/access)?', get=False, post=False)
@comp_dec.Regions
@decorator.node_process
def access(model, node_id):
    return _node.access_node(model, 'iris', int(node_id))