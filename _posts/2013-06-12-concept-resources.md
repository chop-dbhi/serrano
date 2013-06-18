---
layout: page
title: "Concept Resources"
category: ref
date: 2013-06-12 08:54:47
order: 2
---

## Endpoints

Concepts are automatically filtered based on various criteria based on the requesting user's access level. This includes permissions, whether the concepts are published vs. archived, etc.

### `/api/concepts/`

Resource exposing all concepts

#### GET

### `/api/concepts/:id/`

Resource exposing a single concept

#### GET

### `/api/concepts/:id/fields/`

Resource exposing a single concept's related fields. Read more about the [fields response]({{ site.baseurl }}{% post_url 2013-06-12-field-resources%}#response).

#### GET

## Parameters

These are supported as GET paramaters, e.g. /api/concepts/?sort=name&query=cochlear

### sort

The properties/fields to sort the concepts by.

- `category` _(default)_ - sort by the category the concept is contained in and by the order relative to the category
- `name` - sort by the name of the concept

### order

The order of the sorting based on the sort method above.

- `asc` _(default)_ - ascending order
- `desc` - descending order

### published

_Privileged Users Only_

Enables toggling whether to explicitly show only published or unpublished objects. By default both sets are used.

- `true` - filters the published objects
- `false` - filters the unpublished objects

### archived

_Privileged Users Only_

Enables toggling whether to explicitly show only archived or unarchived objects. By default both sets are used.

- `true` - filters the archived objects
- `false` - filters the archived objects

### query

A query term to be used to filter concepts.

- `<query term>` - Performs a robust search across metadata and the data values themselves
  - Each term is queried independently by default
  - A `-` prefix to a term will cause a negation on that term, e.g. `-candy`
  - Quotes around a series of terms will be perform a verbatim search, e.g. `"greek yogurt"`
  - Terms can be combined for a complex lookup, e.g. `dessert -candy "greek yogurt"`

### embed

A flag denoting whether the concept related fields should be embedded in the response.

- `true` - embeds field metadata for each concept
- `false` _(default)_ - references fields with minimal information such as name, id, and the _self_ link

## Response

_Note: setting `embed` to true will add an additional field `fields` which is an array of [fields]({{ site.baseurl }}{% post_url 2013-06-12-field-resources%}#response) related to the concept._

```javascript
{
    "_links": {
        "self": {
            "href": "http://127.0.0.1:8002/api/concepts/1069/", 
            "rel": "self"
        }
    }, 
    "archived": false, 
    "category": {
        "id": 3, 
        "name": "Genomics", 
        "order": 4.0, 
        "parent": null
    }, 
    "description": "",
    "formatter_name": "Formatter", 
    "id": 1069, 
    "keywords": "", 
    "modified": "2013-03-28T18:06:59.944", 
    "name": "File Format", 
    "order": 0.0, 
    "plural_name": "File Formats", 
    "published": true, 
    "queryview": "QueryView", 
    "sortable": true
}
```
