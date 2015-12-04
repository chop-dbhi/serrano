Category = {
    'fields': [':pk', 'name', 'order', 'parent_id'],
    'allow_missing': True,
}

BriefField = {
    'fields': [':pk', 'name', 'description'],
    'aliases': {
        'name': '__unicode__',
    },
    'allow_missing': True,
}

Field = {
    'fields': [
        ':pk', 'name', 'plural_name', 'description', 'keywords',
        'app_name', 'model_name', 'field_name',
        'modified', 'published', 'operators',
        'simple_type', 'internal_type', 'data_modified', 'enumerable',
        'searchable', 'unit', 'plural_unit', 'nullable', 'order'
    ],
    'aliases': {
        'name': '__unicode__',
        'plural_name': 'get_plural_name',
        'plural_unit': 'get_plural_unit',
    },
    'allow_missing': True,
}

BriefConcept = {
    'fields': [':pk', 'name', 'description'],
    'allow_missing': True,
}

Concept = {
    'fields': [
        ':pk', 'name', 'plural_name', 'description', 'keywords',
        'category_id', 'order', 'modified', 'published',
        'formatter', 'queryable', 'sortable', 'viewable'
    ],
    'aliases': {
        'name': '__unicode__',
        'plural_name': 'get_plural_name',
    },
    'allow_missing': True,
}

Context = {
    'exclude': ['user', 'session_key'],
    'allow_missing': True,
}


View = {
    'exclude': ['user', 'session_key'],
    'allow_missing': True,
}

User = {
    'fields': [':pk', 'name', 'username', 'email'],
    'aliases': {
        'name': 'get_full_name',
    }
}

BriefQuery = {
    'include': [':pk', 'name', 'context_json', 'view_json'],
    'allow_missing': True,
}

ForkedQuery = {
    'fields': [':pk', 'parent'],
    'allow_missing': True,
}

Query = {
    'fields': [':pk', 'accessed', 'name', 'description', 'user',
               'shared_users', 'context_json', 'view_json', 'public'],
    'related': {
        'user': User,
        'shared_users': User,
    }
}

Revision = {
    'exclude': ['user', 'session_key', 'data'],
    'allow_missing': True,
}
