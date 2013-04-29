# Field core fields and properties

DataCategory = {
    'fields': [':pk', 'name', 'order', 'parent'],
    'related': {
        'parent': {
            'fields': [':pk', 'name', 'order'],
        }
    },
    'allow_missing': True,
}

Field = {
    'fields': [
        ':pk', 'name', 'plural_name', 'description', 'keywords',
        'category', 'app_name', 'model_name', 'field_name',
        'modified', 'published', 'archived', 'operators',
        'simple_type', 'internal_type', 'data_modified', 'enumerable',
        'searchable', 'unit', 'plural_unit', 'nullable'
    ],
    'aliases': {
        'plural_name': 'get_plural_name',
        'plural_unit': 'get_plural_unit',
    },
    'related': {
        'category': DataCategory,
    },
    'allow_missing': True,
}

Concept = {
    'fields': [
        ':pk', 'name', 'plural_name', 'description', 'keywords',
        'category', 'order', 'modified', 'published', 'archived',
        'formatter_name', 'queryview', 'sortable'
    ],
    'aliases': {
        'plural_name': 'get_plural_name',
    },
    'related': {
        'category': DataCategory,
    },
    'allow_missing': True,
}

ConceptField = {
    'fields': ['alt_name', 'alt_plural_name'],
    'aliases': {
        'alt_name': 'name',
        'alt_plural_name': 'get_plural_name',
    },
    'allow_missing': True,
}


Context = {
    'fields': [':pk', ':local', 'language'],
    'exclude': ['user', 'session_key'],
    'allow_missing': True,
}


View = {
    'exclude': ['user', 'session_key'],
    'allow_missing': True,
}
