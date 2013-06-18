---
layout: page
title: "Base Resources"
category: ref
date: 2013-06-12 08:54:47
order: 0
---

Serrano comes with a base resource that provide structure for the exposed resources. This is described here to make it easier to define other Avocado-backed resources for the most common use cases.

## Behavior

- Every request is checked for authentication if [required]({{ site.baseurl }}{% post_url 2013-06-12-settings%}#serrano_auth_required). This also includes token-based access if [enabled]({{ site.baseurl }}{% post_url 2013-06-12-api-tokens%}).
- If [cross-origin resource sharing]({{ site.baseurl }}{% post_url 2013-06-12-settings%}#serrano_cors_enabled) is enabled, every response gets two additional headers `Access-Control-Allow-Origin` and `Access-Control-Allow-Methods`.

## Methods

### `get_params`

Takes the `request` object and returns a cleaned dict of GET parameters. This uses a restlib2 [Parametizer class](https://github.com/bruth/restlib2/wiki/Parametizer) to clean the parameters.

```python
resource = BaseResource()
params = resource.get_params(request)
```

To customize the clean of parameters and for setting defaults, create a subclass of `restlib2.params.Parametizer` and set it to the `parametizer` on the resource class. For example:

```python
from restlib2.params import Parametizer, param_cleaners
from serrano.resources.base import BaseResource

class MyParametizer(Parametizer):
    query = ''
    page = 1
    per_page = 10

    def clean_page(self, value):
        return param_cleaners.clean_int(value)

    def clean_per_page(self, value):
        return param_cleaners.clean_int(value)    

class MyResource(BaseResource):
    parametizer = MyParametizer
```

### `get_context`

Takes the `request` object and returns a `DataContext` object that is currently applicable to the request. For convenience, the method also takes an `attrs` keyword argument that would be the context nodes themselves. A series of checks are performed:

- If `attrs` are not supplied, derive `attrs` from `request` object using the `context` key
    - For instance, if a POST request was being handled and the POST data contained a key `context`, that would be processed
- If `attrs` is a `dict`, validate and return
- If `attrs` is an integer, lookup the context object for the requesting user and return
- Attempt to current the session context for the user if one exists
- Fallback to an empty context

```python
resource = BaseResource()
context = resource.get_context(request)
# Supply explicit context data
context = resource.get_context(request, attrs={'field': 1, 'operator': 'exact', 'value': 5})
```

### `get_view`

This method is identical to the above `get_context` regarding the processing steps. The difference, of course, is that is assumes valid `DataView` data and it returns a `DataView` instance.

```python
resource = BaseResource()
view = resource.get_view(request)
# Supply explicit view data
view = resource.get_view(request, attrs={'columns': [3, 2, 1]})
```
