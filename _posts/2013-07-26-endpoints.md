---
layout: page
title: "Endpoints"
category: ref
date: 2013-07-26 08:44:20
order: 1
---

The listing below assumes the mount point of the API is `/api/`. URL path segments starting with a colon (:) represents a variable of the specified type such as `int` or `str`. For example, `/api/fields/:int/` matches `/api/fields/1/`, but not `/api/fields/foo/`.

### [Field]({{ site.baseurl }}{% post_url 2013-06-12-field-resources %})

These resources correspond to the `DataField` model in Avocado.

- `/api/fields/`
- `/api/fields/:int/`
- `/api/fields/:int/values/`
- `/api/fields/:int/dist/`
- `/api/fields/:int/stats/`

### [Concept]({{ site.baseurl }}{% post_url 2013-06-12-concept-resources %})

These resources correspond to the `DataConcept` model in Avocado.

- `/api/concepts/`
- `/api/concepts/:int/`
- `/api/concepts/:int/fields/`

### View

These resources correspond to the `DataView` model in Avocado.

- `/api/views/`
- `/api/views/:int/`

### Context

These resources correspond to the `DataContext` model in Avocado.

- `/api/contexts/`
- `/api/contexts/:int/`

### Query

These resources correspond to the `DataQuery` model in Avocado.

- `/api/queries/`
- `/api/queries/:int/`

### Preview

- `/api/data/preview/`

### Export

These resources correspond to the `DataContext` model in Avocado.

- `/api/data/export/`
