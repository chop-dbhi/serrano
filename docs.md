# Overview

Serrano implements a hypermedia API for [Avocado](http://cbmi.github.com/avocado/). Avocado is a Django app which targets _developers who are interested in letting their data do the work for them_.

# Install

```bash
pip install serrano
```

# Configure

Include `serrano.urls` in your `ROOT_URLCONF` (the main **urls.py**):

```python
urlpatterns = patterns('',
    ...
    url(r'^api/', include('serrano.urls')),
    ...
)
```

In this example, `/api/` is the root endpoint for Serrano. Hitting this endpoint will expose the available URLs for the API.

# Media Types

Serrano is a Hypermedia API implementation for Avocado, a metadata API app for Django. Defined here are the media types Serrano uses to represent data structures corresponding to those in Avocado.

## application/vnd.serrano.query-context+json

### Definition

A JSON-based media type representing a condition tree structure for Avocado, a Metadata API app for Django.

### Description

A tree structure with two types of nodes, **condition** and **branch**. 

### Node Types

#### Condition

```javascript
{
	"id": <id>,
	"operator": <operator>,
	"value": <value>
}
```

### Branch

```javascript
{
	"type": <type>,
	"children": [<node>, <node> [, ...]]
}
```

### Node Elements

#### Condition Node

##### `id`
The value can be:

- An `int` representing the primary key identifer for a `DataField` instance, e.g. `1`
- Period-delimited `string` representing a natural key for a `DataField` instance, e.g. `'app.model.field'`
- An `array` of strings representing a natural key for a `DataField` instance, e.g. `["app", "model", "field"]`

##### `operator`
A `string` representing a valid `DataField` operator. Valid operators vary depending on the implementation, but should be validated downstream.

##### `value`
Any valid JSON data type.

#### Branch Node

##### `type`
A `string` that is `"and"` or `"or"` representing the type of branch or logical operation between child nodes defined in the `children` property.

##### `children`
An `array` of _two_ or more nodes.


### Examples

#### Single Condition

```javascript
{
	"id": 2,
	"operator": "iexact",
	"value": 50
}
```

#### Branch with Two Conditions

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

#### Branch with One Condition and One Branch

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


# Resources

## DataField

Descriptive and other various metadata about `DataField` objects.

### Schema

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
    "url": "http://example.com/api/fields/1/",
    "modified": "2012-02-04T15:11:03Z",
    "published": true,
    "archived": false,
    "data": {
        "type": "string",
        "enumerable": true,
        "modified": "2011-10-01T11:05:10Z",
        "size": 7
    },
    "links": {
    	"values": {
    		"rel": data,
    		"href": "http://example.com/api/fields/1/values/"
    	},
        "aggregates": {
            "rel": "data",
            "href": "http://example.com/api/fields/1/aggregates/"
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

### Endpoints

- `/api/fields/` - Array of `DataField` objects _(privileged users will also see unpublished
and archived data)_
- `/api/fields/:id/` - Single `DataField` object

### Parameters

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

### Links

- `stats` - link to aggregation data about the `DataField`
- `distribution` - link to distribution data for the `DataField`
- `concepts` - link to `DataConcept` objects in which this `DataField` is related to

## DataField Values

Returns an array of distinct values for this `DataField`.

### Schema

```javascript
[
	{
		"name": "Value 1",
		"value": "value1
	},
	...
]
```

### Endpoints

- `/api/fields/:id/values/` - Unique values for a `DataField`.

**Note:** This endpoint may be used when a datafield is flagged as `searchable` and can same a query parameter `q` for performing searches on the values themselves.

A convention for better search implementations is to override the URL to point to a different resource which supports the same media types.

### Parameters

_query_

- `<query term>` - Performs a `LIKE` search on the values themselves

## DataField Stats

Various statistics about a particular `DataField`.

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
    "mode": null,
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

### Links

- `parent` - link to the corresponding `DataField` resource


## DataField Distributions

Dynamic resource for generating distribution data between one or more datafields. For each 

### Schema

```javascript
{
	"clustered": true,
	"data": [
		{
			"count": "Foo",
			"values": [[...], ...]
		},
		...
	]
}
```

### Endpoints

- `/api/fields/<pk>/dist/` - Defines a distribution between one or more `DataField`s

### Parameters

_dimension_

- `<pk>` - Add a dimension to the distribution. Multiple dimensions can be provided using multiple GET parameters, e.g. `/api/fields/3/distribution/?dimension=4&dimension=6`

_nulls_

- `false` _(default)_ - Exclude `NULL` values from distribution
- `true` - Include `NULL` values in distribution. Note, for continuous data that is clustered, nulls are removed.

_cluster_

- `null` _(default)_ - If the vector size exceeds this threshold, the data is down-sampled to a more reasonable size based on the current size of the data. Note, this sampling is now an approximation of the data and information is lost.
- `true` - Explicitly cluster the distribution regardless of the size
- `false` - Do not cluster



# Client Tools & Interfaces

Having a hypermedia API is great, but without a client to consume it, it is somewhat useless.
Here are a few tools to get you started.

## JavaScript

### Install

The script is wrapped using the Universal Module Definition (UMD), which means it can be used in a browser, Node, or AMD environment.

Use it as a module:

```javascript
require(['serrano'], function(Serrano) {
	// ...
});
```

or as a traditional script:

```html
<script src="/path/to/serrano.js"></script>
```

### Usage

The script exposes a `Serrano` object which consists of `Backbone.Model` classes and convenience methods for interacting with the session instance.

```javascript
// Instance of DataContextView
Serrano.session.datacontext
```

## Cilantro

[Cilantro](http://cbmi.github.com/cilantro/) is Web browser-based client that provides a
clean browsable interface for viewing and interacting with the data.