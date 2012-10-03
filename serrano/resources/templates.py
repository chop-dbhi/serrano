# DataField core fields and properties
DataField = {
    'fields': [
        ':pk', 'name', 'plural_name', 'description', 'keywords',
        'category', 'app_name', 'model_name', 'field_name',
        'modified', 'published', 'archived', 'operators',
        'simple_type', 'internal_type', 'data_modified', 'enumerable',
        'searchable', 'unit', 'plural_unit'
    ],
    'key_map': {
        'plural_name': 'get_plural_name',
        'plural_unit': 'get_plural_unit',
        'operators': 'operator_choices',
    },
    'related': {
        'category': {
            'fields': [':pk', 'name', 'order', 'parent_id']
        },
    },
}

DataConcept = {
    'fields': [
        ':pk', 'name', 'plural_name', 'description', 'keywords',
        'category', 'order', 'modified', 'published', 'archived',
        'formatter', 'queryview'
    ],
    'key_map': {
        'plural_name': 'get_plural_name',
    },
    'related': {
        'category': {
            'fields': [':pk', 'name', 'order', 'parent_id']
        },
    },
}

DataConceptField = {
    'fields': ['alt_name', 'alt_plural_name'],
    'key_map': {
        'alt_name': 'name',
        'alt_plural_name': 'get_plural_name',
    },
}


DataContext = {
    'fields': [':pk', ':local', 'language'],
    'exclude': ['user', 'session_key'],
}


DataView = {
    'exclude': ['user', 'session_key'],
}
