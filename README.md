Entrée - Django powered SSO
===========================

Simple django-based Single sign-on system.



Configuration
=============


Server-side
-----------


**settings.py**

```python

MIDDLEWARE_CLASSES = (
    ...
    'entree.enauth.middleware.AuthMiddleware',
    ...
)

INSTALLED_APPS = (
    ...
    'entree.enauth',
    'entree.site',
    'bootstrap',
    ...
)


TEMPLATE_CONTEXT_PROCESSORS = (
    ...
    'entree.common.context_processors.common',
    ...
)

AUTHENTICATION_BACKENDS = (
    'entree.enauth.backends.AuthBackend',
    'django.contrib.auth.backends.ModelBackend',
)

ENTREE = {
    "VERSION": 1,
    'URL_SERVER': 'http://entree.example.com',
    'CACHE_PROFILE': 5*60,
    'ROUTE': {
        'JS_LIB': '/static/js/entree.js',
    },

    'COOKIE': {
        'ANONYMOUS_VALUE': 'ANONYMOUS',
    },

    'NOSITE_ID': 1,
    'DEFAULT_SITE': 4,
    'SESSION_KEY': 'entree_session',
    'STORAGE_TOKEN_KEY': 'entree_token',
}
```




Client-side
-----------

**settings.py**

```python
MIDDLEWARE_CLASSES = (
    ...
    'entree.client.middleware.AuthMiddleware',
    ...
)

TEMPLATE_CONTEXT_PROCESSORS = (
    ...
    'entree.common.context_processors.common',
    ...
)

INSTALLED_APPS = (
    'entree.client',
    'entree.client.db',
)


ENTREE = {
    "ROUTE": {
        "PROFILE": "/profile/",
        "PROFILE_FETCH": "/profile/fetch/",
        "REGISTER": "/register/",
        "JS_LIB": "/static/js/entree.js",
        "LOGOUT": "/logout/",
        "LOGIN": "/login/",
        "PROFILE_EDIT": "/profile/edit/"
    },
    "SITE_ID": 3,
    "COOKIE": {
        "PATH": "/",
        "ANONYMOUS_VALUE": "ANONYMOUS",
        "INVALID": "INVALID",
        "NAME": "entree_token",
        "DOMAIN": "localhost"
    },
    "URL_SERVER": "http://entree.example.com",
    "SECRET_KEY": "IcW211vIIx8EZZD0wlkWaCF06Tp55SMeO9g82o5F",
    "CACHE_PROFILE": 300
}
```


You have to choose `entree.client.db` or `entree.client.cache` app.
The `db` one inherits Entree's user from Django's User.
The `cache` app does not use models, it just push things into cache.



TODOs:
======


- client's data pushing
...
