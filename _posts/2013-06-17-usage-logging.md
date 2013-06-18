---
layout: page
title: "Usage Logging"
category: ref
date: 2013-06-17 10:56:52
order: 3
---

Serrano makes use of Avocado's metrics API for logging usage information of Serrano's endpoints. The information can be analyzed for determining user trends. Below are the usage events broken down by the primary data type. Each event may capture additional data which are denoted by a sub-list.

### Concept

- `read` - Access a specific concept
- `fields` - Access a concept's fields. This is a more fine-grain access than `read` since it implies _diving in_ to the underlying field data itself.
- `search` - Search for concepts
    - `query` - The query term used

### Field

- `read` - Access a specific field
- `search` - Search for fields
    - `query` - The query term used
- `dist` - Access a field's distribution
    - `size` - Number of points involved
    - `clustered` - Boolean denoting if clustering was used
    - `aware` - Denotes whether the distribution is context-aware or not
- `stats` - Access a field's data statistics
- `values` - Search for a field's underyling data values
    - `query` - The query term used
- `validate` - Use of the field valiation endpoint
    - `count` - The number of values being validated

### Context

- `read` - Access a context
- `create` - Create a context
- `update` - Update a context
- `delete` - Delete a context

### View

- `read` - Access a context
- `create` - Create a context
- `update` - Update a context
- `delete` - Delete a context

### Other

- `export` - An export has been requested
    - `type` - The type of export, e.g. CSV, R, etc.
    - `partial` - A boolean denoting whether this was a full or partial export (single or range of pages).
