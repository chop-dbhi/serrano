---
layout: page
title: "Context Mediatype"
category: ref
date: 2013-06-12 08:54:47
order: 5
---

**Official mediatype:** application/vnd.serrano.context+json

A JSON-based media type representing a condition tree structure corresponding to Avocado's `DataContext` model. This is tree structure with two types of nodes: **condition** and **branch**.

## Condition Node Format

Represents a single query condition

```javascript
{
    "field": <field>,
    "operator": <operator>,
    "value": <value>,
    "nulls": <nulls>,
    "concept": <concept>,
    "lang": <lang>,
    "enabled": <enabled>,
    "warnings": [<warning>, [...]],
    "errors": [<error>, [...]]
}
```

### field

**Required.** The value can be:

- An integer representing the primary key identifer for a `DataField` instance, e.g. `1`
- Period-delimited string representing a natural key for a `DataField` instance, e.g. `"app.model.field"`
- An array of strings representing a natural key for a `DataField` instance, e.g. `["app", "model", "field"]`

### operator

**Required.** A string representing a valid `DataField` operator. Valid operators are supplied with the field metadata, but will be validated when the node is sent to the server.

### value

**Required.** Any valid JSON data type that is appropriate for the type of the `DataField`. If the type is invalid, a validation error will occur.

### nulls

A boolean denoting whether to include `NULL` values. Depending on the underlying data, `NULL` values may be considered novel and should not be excluded from the set. Default is `false`

### concept

An integer representing the primary key identifier of the `DataConcept` the field is contained in. Clients that take advantage of concepts will likely need to supply this in order to correctly repopulate and/or organize data on the client.

### lang

A read-only string that is a natural language representation of the node. This is annotated server-side and is used for information purposes and future validation purposes.

### enabled

A boolean that is used during re-validation of the node on the server. If the node is no longer valid due to data changes or the field is not longer available, this flag is set to `false`. Clients may provide the option to override this auto-disabling policy for nodes with only warnings (not errors) by changing the flag to `true`. This is preferred over removing the flag to prevent the re-validation process happening subsequent times.

### warnings

A read-only array of warnings that result during re-validation of the node. This typically includes changes to the data that caused the condition to be _out of range_ such as a numerical condition that exceeds the upper bound of the data which would result in no results. These are considered warnings since there is no harm in applying the conditions.

### errors

A read-only array of errors that result during re-validation of the node. Errors are different from warnings in that the node is considered _broken_ and cannot be enabled. Clients may choose to remove the node from the tree or leave it for historical reasons.

## Branch Node Format

```javascript
{
    "type": <type>,
    "children": [<node>, <node> [, ...]]
}
```

### type

**Required.** A string that is `"and"` or `"or"` representing the type of branch or logical operation between child nodes defined in the `children` property.

### children

An array of _two_ or more condition and/or branch nodes.

## Example

```javascript
{
    "type": "or",
    "children": [{
        "field": 2,
        "operator": "gte",
        "value": 50,
        "nulls": true,
        "lang": "Building Age is greater than or equal to 50 or unknown" 
    }, {
        "type": "and",
        "children": [{
            "field": 1,
            "operator": "in",
            "value": ["Allentown", "Philadelphia"],
            "lang": "City is either Allentown or Philadelphia"
        }, {
            "field": 5,
            "operator": "in",
            "value": ["Studio", "One-Bedroom"],
            "lang": "Apartment Type is either Studio or One-Bedroom"
        }]
    }]
}
```


