from framework.errors.exceptions import DCException
from framework.machinery import component
from dycm import wysiwyg
from . import model
from framework.util import html, clean


__author__ = 'Justus Adam'
__version__ = '0.2'


DEFAULT_FIELD_HANDLER_NAME = 'FieldHandler'


# @component.Component('FieldTypes')
# class Fields(lazy.Loadable):
#     @component.inject_method('Modules')
#     def __init__(self, m):
#         super().__init__()
#         self._inner = None
#         self.modules = m
#
#     def _get_handler(self, string: str):
#         module, *function = string.split('.', 1)
#         return getattr(self.modules[module],
#             function if function else DEFAULT_FIELD_HANDLER_NAME)
#
#     def load(self):
#         self._inner = {
#             a.machine_name: self._get_handler(a.handler)
#             for a in model.FieldType.select()
#         }
#
#     @lazy.ensure_loaded
#     def __getitem__(self, item):
#         return self._inner[item]


@component.inject(fields='fields')
def field(field_type, fields):
    def inner(class_):
        fields[field_type] = class_
        return class_

    return inner


class FieldExists(DCException):
    pass


class _Field(object):
    def __init__(self, config, page_type):
        super().__init__()
        self.config = config
        self.page_type = page_type

    @property
    def name(self):
        return self.config.field_type.machine_name

    def access(self, page_id):
        db_obj = self.from_db(page_id)
        return dict(
            content=html.ContainerElement(
                db_obj.content, classes={'field', f'field-{self.name}'}
            ),
            title=self.get_field_title(),
        )

    def edit(self, page_id):
        try:
            db_obj = self.from_db(page_id)
            return dict(
                name=self.name,
                content=wysiwyg.WysiwygTextarea(
                    db_obj.content,
                    classes={'field', f'field-{self.name}', 'edit'},
                    name=self.name,
                ),
            )
        except:
            raise

    def process_edit_request(self, page_id, content):
        try:
            db_obj = self.from_db(page_id)
            db_obj.content = clean.remove_dangerous_tags(content)
            db_obj.save()
        except:
            raise

    def from_db(self, page_id):
        return model.field(self.name).get(
            page_id=page_id,
            page_type=self.page_type
        )

    def add(self):
        return dict(
            name=self.name,
            content=wysiwyg.WysiwygTextarea(
                classes={'field', f'field-{self.name}', 'edit'}, name=self.name
            ),
        )

    def process_add(self, page_type, page_id, content):
        model.field(self.name).create(
            content=clean.remove_dangerous_tags(content),
            page_id=page_id,
            page_type=page_type
            )

    def get_field_title(self):
        return self.name


Field = _Field
