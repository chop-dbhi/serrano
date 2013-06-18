---
layout: page
title: "Field Resources"
category: ref
date: 2013-06-12 08:54:47
order: 1
---

Fields are automatically filtered based on various criteria based on the requesting user's access level. This includes permissions, whether the fields are published vs. archived, etc.

### `/api/fields/`

Resource exposing all available fields.

### Methods

#### GET

##### Parameters

- **sort** - The properties/fields to sort the fields by.
    - `category` (default) - sort by the category the field is contained in and by the order relative to the category
    - `name` - sort by the name of the field
- **order** - The order of the sorting based on the sort method above.
    - `asc` (default) - ascending order
    - `desc` - descending order
- **published** - _Privileged Users Only_ Enables toggling whether to explicitly show only published or unpublished objects. By default both sets are used.
    - `true` - filters the published objects
    - `false` - filters the unpublished objects
- **archived** - _Privileged Users Only_ - Enables toggling whether to explicitly show only archived or unarchived objects. By default both sets are used.
    - `true` - filters the archived objects
    - `false` - filters the archived objects
- **query** - A query term to be used to filter fields.
    - `<query term>` - Performs a robust search across metadata and the data values themselves
        - Each term is queried independently by default
        - A `-` prefix to a term will cause a negation on that term, e.g. `-candy`
        - Quotes around a series of terms will be perform a verbatim search, e.g. `"greek yogurt"`
        - Terms can be combined for a complex lookup, e.g. `dessert -candy "greek yogurt"`

---

### `/api/fields/:id/`

Resource exposing a single field.

### Methods

#### GET


---

### `/api/fields/:id/values/`

Resource exposing distinct values for a specific field.

### Methods

#### GET

- **query** - Same as above
- **aware** - Toggles resource to be _context-aware_. Depending on the context, this may result in a subset of values returned.
    - `false` (default) - Make context-naive
    - `true` - Make context-aware
- **random** - Returns a random set of values up to `N`
    - `N` - The number of random values to return, e.g. `5`

---

### `/api/fields/:id/dist/`

Resource exposing a distribution API. One or more dimensions can be specified and counts will be returned for each unique group. For large data sets, k-means clustering will be performed and will result in weighted counts based on euclidean distance from the nearest centroid.

### Methods

#### GET

- **dimensions** - One or more fields to group by
- **nulls** - Flag for whether NULL values are included in the result set
    - `false` (default) - Do not include
    - `true` - Include
- **aware** - Flag for whether the response will be _context-aware_. The response will contain data relative to the current context.
    - `false` (default) - Make context-naive
    - `true` - Make context-aware
- **sort** - The properties/fields to sort the data points by
    - `fields` (default) - Sorts by the dimensions (fields) specified
    - `count` - Sort by the count
- **cluster** - Flag for whether clustering should be applied.
    - `true` (default) - Enable clustering (note, this requires a minimum of 500 data points to act on)
    - `false` - Disable clustering
- **n** - The number of clusters to use when computing weighted counts, e.g. 5. If not specified, the cluster count is determined based on the number of data points.

___

### JSON Response

```javascript
{
    "_links": {
        "self": {
            "href": "http://127.0.0.1:8002/api/fields/2149/", 
            "rel": "self"
        }, 
        "values": {
            "href": "http://127.0.0.1:8002/api/fields/2149/values/", 
            "rel": "data"
        }
    }, 
    "alt_name": null, 
    "alt_plural_name": "File Formats", 
    "app_name": "bulkup", 
    "archived": false, 
    "data_modified": null, 
    "description": null, 
    "enumerable": false, 
    "field_name": "file_format", 
    "id": 2149, 
    "internal_type": "char", 
    "keywords": null, 
    "model_name": "uploadeddatafile", 
    "modified": "2013-03-28T18:06:22.670", 
    "name": "File Format", 
    "nullable": false, 
    "operators": [
        [
            "exact", 
            "is"
        ], 
        [
            "-exact", 
            "is not"
        ], 
        [
            "iexact", 
            "is"
        ], 
        [
            "-iexact", 
            "is not"
        ], 
        [
            "in", 
            "includes"
        ], 
        [
            "-in", 
            "excludes"
        ], 
        [
            "icontains", 
            "contains"
        ], 
        [
            "-icontains", 
            "does not contain"
        ]
    ], 
    "plural_name": "File Formats", 
    "plural_unit": null, 
    "published": true, 
    "searchable": true, 
    "simple_type": "string", 
    "unit": null
}
```
