---
layout: page
title: "Install & Setup"
category: doc
date: 2013-06-12 08:54:47
order: 0
---

## Install

Serrano's source code is hosted on [GitHub](https://github.com/cbmi/serrano). Releases follow the [SemVer](http://semver.org/) spec. All tagged versions are uploaded to [PyPi](https://pypi.python.org/pypi), but tagged versions can be [downloaded directly](https://github.com/cbmi/serrano/tags).

```bash
pip install serrano --use-mirrors
```

## Setup

Include `serrano.urls` in your `ROOT_URLCONF` module:

```python
urlpatterns = patterns('',
    url(r'^api/', include('serrano.urls')),
    ...
)
```
In this example, `/api/` is the root endpoint for Serrano. Hitting this endpoint will expose the available URLs for the API.

Add `django.contrib.sessions` to your project's `INSTALLED_APPS`:

```python
INSTALLED_APPS = (
    'django.contrib.sessions',
    ...
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
```

---

#### Next: [Settings]({{ site.baseurl }}{% post_url 2013-06-12-settings %})
