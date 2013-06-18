---
layout: page
title: "API Tokens"
category: doc
date: 2013-06-12 08:54:47
---

Serrano supports token-based access using a temporary session-based API token. Users must send an initial POST request to Serrano's root endpoint with their credentials. Upon successful authentication, a temporary API token will be created and returned in the response. This token can be supplied with subsequent requests for the remainder of the session (rather than constantly supplying credentials).

## Install & Setup

To install, add `serrano.backends.TokenBackend` to the `AUTHENTICATION_BACKENDS` setting:

```python
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'serrano.backends.TokenBackend',
    ...
)
```

## Settings

### `SERRANO_TOKEN_TIMEOUT`

Integer of seconds until a token expires. Note, the token timeout is fixed and does not reset upon each request. Default is the same as the `SESSION_COOKIE_AGE` Django setting
