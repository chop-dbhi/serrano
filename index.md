---
layout: default
title: "Serrano: Hypermedia APIs for Avocado"
---

<p class=lead>Serrano is a <a href="https://en.wikipedia.org/wiki/Hypermedia">hypermedia</a> implementation for <a href="http://cbmi.github.io/avocado/">Avocado</a> that adheres to the constraints of <a href="https://en.wikipedia.org/wiki/Representational_state_transfer">REST</a>.</p>

---

### Introduction

Serrano defines resources and exposes hypermedia APIs that loosely map to Avocado programmatic APIs. For example, Avocado has the `DataField` model which instances correspond to a field in the data model. Fields can be programmatically defined and accessed:

```python
from avocado.models import DataField

f = DataField('library', 'book', 'title')
f.title = 'Title'
f.description = 'The title of the book'
f.get_plural_name() # Titles
f.simple_type # string
```

Serrano has a resource for `DataField` instances which can be accessed with a URL (assuming the above field's primary key is _1_):

```
GET /api/fields/1/
Accept: application/json
```

The response body has quite a few properties which contain metadata for the field being accessed as well as a `_links` objects which contains related links:

```javascript
{
    "id": 1,
    "app_name": "library",
    "model_name": "book",
    "field_name": "title",
    "category": null,
    "description": "The title of the book",
    "internal_type": "char",
    "keywords": "",
    "modified": "2012-10-11 14:29:43",
    "name": "Title",
    "nullable": false,
    "plural_name": "Titles",
    "published": true,
    "searchable": true,
    "simple_type": "string",
    ...
    "_links": {
        "self": {
            "href": "http://example.com/api/fields/1/",
            "rel": "self"
        },
        ...
    }
}
```

#### Support for Writes

Some resources such as ones corresponding to Avocado's `DataContext`, `DataView`, and `DataQuery` models support `POST`, `PUT`, and `DELETE` requests. This enables clients the ability to manipulate objects of these types they have permission using the API.

```
PUT /api/contexts/1/
Accept: application/json
Content-Type: application/json

{
    "id": 1,
    "json": {
        "field": "1",
        "operator": "icontains",
        "value": "api"
    },
    ...
}
```

### Next Steps

To get started using Serrano, follow the [install & setup guide]({{ site.baseurl }}{% post_url 2013-06-12-install-setup %}).

For more information on what endpoints are defined, view the [list of endpoint]({{ site.baseurl }}{% post_url 2013-07-26-endpoints %}).
