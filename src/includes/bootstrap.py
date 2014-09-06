__author__ = 'justusadam'


DEFAULT_MODULES = [
    "zeus",
    "aphrodite",
    "iris",
    "dionysus",
    "hera"
]
TRACKER_TABLE_CREATION_QUERY = "create table created_tables (id int unsigned not null auto_increment unique primary key, created_table varchar(500) not null unique, source_module_name varchar(500) not null, source_module_id int unsigned not null);"
FILE_DIRECTORIES = {
    "theme": [
        "custom/themes",
        "themes"
    ],
    "private": "custom/files/private",
    "public": "custom/files/public"
}
MODULES_DIRECTORY = "custom/modules"
NECESSARY_MODULE_ATTRIBUTES = [
    "name",
    "role"
]
COREMODULES_DIRECTORY = "coremodules"
MODULE_CONFIG_NAME = "config.json"
