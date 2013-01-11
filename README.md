# Serrano

Serrano implements a hypermedia API for [Avocado](http://cbmi.github.com/avocado/). Avocado is a Django app which targets _developers who are interested in letting their data do the work for them_.

## Install

```bash
pip install serrano
```

## Configure

Include `serrano.urls` in your `ROOT_URLCONF` (the main **urls.py**):

```python
urlpatterns = patterns('',
    ...
    url(r'^api/', include('serrano.urls')),
    ...
)
```

Add `django.contrib.sessions` to your project's `INSTALLED_APPS`:

```python
INSTALLED_APPS = (
    ...
    'django.contrib.sessions',
)

```

Add the `serrano.middleware.SessionMiddleware` to the `MIDDLEWARE_CLASSES`
setting after Django's session and authentication middleware (if installed):

```python
MIDDLEWARE_CLASSES = (
    ...
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'serrano.middleware.SessionMiddleware',
    ...
)

In this example, `/api/` is the root endpoint for Serrano. Hitting this endpoint will expose the available URLs for the API.

## Media Types

Serrano is a Hypermedia API implementation for Avocado. Defined here are the media types Serrano uses to represent data structures corresponding to those in Avocado.

_Note that currently Serrano exposed plain `application/json` representations of the below mediatypes._

### application/vnd.serrano.datacontext+json

#### Definition

A JSON-based media type representing a condition tree structure corresponding to Avocado's `DataContext` model.

#### Description

A tree structure with two types of nodes, **condition** and **branch**. 

#### Node Types

##### Condition

```javascript
{
	"id": <id>,
	"operator": <operator>,
	"value": <value>
}
```

#### Branch

```javascript
{
	"type": <type>,
	"children": [<node>, <node> [, ...]]
}
```

#### Node Elements

##### Condition Node

##### `id`
The value can be:

- An `int` representing the primary key identifer for a `DataField` instance, e.g. `1`
- Period-delimited `string` representing a natural key for a `DataField` instance, e.g. `'app.model.field'`
- An `array` of strings representing a natural key for a `DataField` instance, e.g. `["app", "model", "field"]`

##### `operator`
A `string` representing a valid `DataField` operator. Valid operators vary depending on the implementation, but should be validated downstream.

##### `value`
Any valid JSON data type.

##### Branch Node

##### `type`
A `string` that is `"and"` or `"or"` representing the type of branch or logical operation between child nodes defined in the `children` property.

##### `children`
An `array` of _two_ or more nodes.


#### Examples

##### Single Condition

```javascript
{
	"id": 2,
	"operator": "iexact",
	"value": 50
}
```

##### Branch with Two Conditions

```javascript
{
	"type": "and",
	"children": [{
		"id": 2,
		"operator": "iexact",
		"value": 50
	}, {
		"id": 1,
		"operator": "in",
		"value": ["foo", "bar"]
	}
}
```

##### Branch with One Condition and One Branch

```javascript
{
	"type": "or",
	"children": [{
		"id": 2,
		"operator": "iexact",
		"value": 50
	}, {
		"type": "and",
		"children": [{
			"id": 1,
			"operator": "in",
			"value": ["foo", "bar"]
		}, {
			"id": 1,
			"operator": "in",
			"value": ["baz", "qux"]
		}]
	}]
}
```

### application/vnd.serrano.dataview+json

#### Definition

A JSON-based media type representing an table-based output format corresponding to Avocado's `DataView` model.

#### Description

Contains two properties `columns` and `ordering` which represent the selected output columns for the table and column ordering, respectively. Each _column_ in this context corresponds to a `DataConcept`.

#### Example

```
{
    "columns": [3, 1, 8],
    "ordering": [[1, 'desc']],
}
```


## Resources

### DataField

Descriptive and other various metadata about `DataField` objects.

#### Schema

```javascript
{
    "id": 4,
    "name": "Ethnicity",
    "name_plural": "Ethnicities",
    "description": "The fact or state of belonging to a social group that has a common national or cultural tradition",
    "keywords": "",
    "unit": null,
    "unit_plural": null,
    "category" : {
        "id": 2,
        "name": "Demographics",
        "order": 1,
        "parent_id": null
    },
    "app_name": "patient",
    "model_name": "demographics",
    "field_name": "ethnicity",
    "modified": "2012-02-04T15:11:03Z",
    "created": "2012-02-04T15:11:03Z",
    "published": true,
    "archived": false,
    "simple_type": "string",
    "internal_type": "char",
    "enumerable": true,
    "searchable": false,
    "data_modified": "2011-10-01T11:05:10Z",
    "links": {
        "self": {
            "rel": "self",
            "href": "http://example.com/api/fields/1/",
        },
    	"values": {
            "rel": "data",
            "href": "http://example.com/api/fields/1/values/"
    	},
    	"stats": {
            "rel": "data",
            "href": "http://example.com/api/fields/1/stats/"
    	},
        "distribution": {
            "rel": "data",
            "href": "http://example.com/api/fields/1/distribution/"
        },
        "concepts": {
            "rel": "related",
            "href": "http://example.com/api/fields/1/concepts/"
        }
    }
}
```

#### Endpoints

- `/api/fields/` - Array of `DataField` objects _(privileged users will also see unpublished
and archived data)_
- `/api/fields/:id/` - Single `DataField` object

#### Parameters

_sort_

- `category` _(default)_ - sort by the category (which is sorted by the order)
- `name` - sort by the name

_direction_

- `desc` _(default)_ - descending order
- `asc` - ascending order

_published (for privileged users)_

- `true` - filters the published objects
- `false` - filters the unpublished objects

_archived (for privileged users)_

- `true` - filters the archived objects
- `false` - filters the archived objects

_query_

- `<query term>` - Performs a robust search across metadata and the data values themselves

#### Links

- `stats` - link to aggregation data about the `DataField`
- `distribution` - link to distribution data for the `DataField`
- `concepts` - link to `DataConcept` objects in which this `DataField` is related to

### DataField Values

Returns an array of distinct values for this `DataField`.

#### Schema

```javascript
[
	{
		"name": "Value 1",
		"value": "value1"
	},
	...
]
```

#### Endpoints

- `/api/fields/:id/values/` - Unique values for a `DataField`.

**Note:** This endpoint may be used when a datafield is flagged as `searchable` and can same a query parameter `q` for performing searches on the values themselves.

A convention for better search implementations is to override the URL to point to a different resource which supports the same media types.

#### Parameters

_query_

- `<query term>` - Performs a `LIKE` search on the values themselves

### DataField Stats

Various statistics about a particular `DataField`. The output of this is dependent on the data type.

### Schema

```javascript
{
    "size": null,
    "count": null,
    "max": null,
    "min": null,
    "avg": null,
    "sum": null,
    "stddev": null,
    "variance": null,
    "links": {
        "parent": {
            "rel": "parent",
            "href": "http://example.com/api/fields/1/"
        }
    }
}
```

### Endpoints

- `/api/fields/:id/stats/` - Statistical data specific to the `DataField` object

#### Links

- `parent` - link to the corresponding `DataField` resource


### DataField Distribution

Dynamic resource for generating distribution data between one or more `DataField`s. This resource is only available if Numpy and SciPy has been installed as an optional dependency for Avocado.

#### Schema

```javascript
{
    "clustered": true,
    "data": [
        {
            "count": "Foo",
            "values": [[...], ...]
        },
        ...
    ],
    "outliers": [
        ...
    ]
}
```

#### Endpoints

- `/api/fields/:id/dist/` - Defines a distribution between one or more `DataField`s

#### Parameters

_dimension_

- `:id` - Add a dimension to the distribution. Multiple dimensions can be provided using multiple GET parameters, e.g. `/api/fields/3/distribution/?dimension=4&dimension=6`

_nulls_

- `false` _(default)_ - Exclude `NULL` values from distribution
- `true` - Include `NULL` values in distribution. Note, for continuous data that is clustered, nulls are removed.

_cluster_

- `null` _(default)_ - If the vector size exceeds this threshold, the data is down-sampled to a more reasonable size based on the current size of the data. Note, this sampling is now an approximation of the data and information is lost.
- `true` - Explicitly cluster the distribution regardless of the size
- `false` - Do not cluster



## Client Tools & Interfaces

Having a hypermedia API is great, but without a client to consume it, it is somewhat useless. [Cilantro](http://cbmi.github.com/cilantro/) is Web browser-based client that provides a clean browsable interface for viewing and interacting with the APIs Serrano provides.


## CHANGELOG

2.0.11 [diff](https://github.com/cbmi/serrano/compare/2.0.10...2.0.11)

- Abstract out logic for resolving `DataView` and `DataContext` objects
- Update tests to require Avocado 2.0.13+

2.0.10 [diff](https://github.com/cbmi/serrano/compare/2.0.9...2.0.10)

- Fix missing increment of `exporter.row_length` for dealing with reundant
rows in Avocado 2.0.9+

2.0.9 [diff](https://github.com/cbmi/serrano/compare/2.0.8...2.0.9)

- Add missing `post` method on data preview resource (from 2.0.7)

2.0.8 [diff](https://github.com/cbmi/serrano/compare/2.0.7...2.0.8)

- Remove map of `operator_choices` to `operators`
    - Change made in Avocado 2.0.10

2.0.7 [diff](https://github.com/cbmi/serrano/compare/2.0.6...2.0.7)

- Add support for defining the `context` and `view` objects via a POST request
    - This enables performing one-off (non-persisted) queries
- Abstract out the browser-based *data preview* resource from the format export mechanism
- Change export endpoint `/api/data/export/` to return an object of possible export formats
    - Each export target has it's own endpoint, e.g. `/api/data/export/sas/` for SAS export

2.0.6 [diff](https://github.com/cbmi/serrano/compare/2.0.5...2.0.6)

- Update django-preserialize 1.0 to make use of the `allow_missing` option
    - This prevents missing keys or attributes from throwing an exception
- Add `DataConcept.sortable` field from Avocado 2.0.8+

2.0.5 [diff](https://github.com/cbmi/serrano/compare/2.0.4...2.0.5)

- #21 - Fix the `ExporterResource` to use the `DjangoJSONEncoder` to correctly handle datetimes and `Decimal`s

2.0.4 [diff](https://github.com/cbmi/serrano/compare/2.0.3...2.0.4)

- Change behavior of `DataContextResource` to recalculate count only [if at least one condition is present](https://github.com/cbmi/serrano/commit/a774621a2788f8b2736e6a5675d5ba6bdeb4163e)
- Integrate history API settings from Avocado 2.0.7+
    - Instances are no longer auto-archived, but [are conditional](https://github.com/cbmi/serrano/commit/73d5ba5a44a5f06ea7342a5f627dc71b621aa09b) based the `HISTORY_ENABLED` setting

2.0.3 [diff](https://github.com/cbmi/serrano/compare/2.0.2...2.0.3)

- Fix incorrect use of `sys.version_info`

2.0.2 [diff](https://github.com/cbmi/serrano/compare/2.0.1...2.0.2)

- Add Python 2.6 support

2.0.1 [diff](https://github.com/cbmi/serrano/compare/2.0.0...2.0.1)

- Fix erroneous reset of kwargs in `DataContextResource` and `DataViewResource`

2.0.0 - Initial release
