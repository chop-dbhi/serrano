# Boolean denoting whether authentication is required to access the API.
AUTH_REQUIRED = False

# Boolean denoting whether Cross-Origin Resource Sharing is enabled.
CORS_ENABLED = False

# List/tuple of hosts for the Access-Control-Allow-Origin response header.
# If cross-origin request is received from an origin not in this list, the
# headers that succeeds the pre-flight request will be not be set. If the
# list is empty, all origins are assumed to be allowed.
CORS_ORIGINS = ()

# Integer of seconds until a token expires. Note, the token timeout is fixed
# and does not reset upon each request. Default is the same as the
# SESSION_COOKIE_AGE Django setting.
TOKEN_TIMEOUT = None

# Integer defining the number of requests that are allowed in any given time
# window defined by RATE_LIMIT_SECONDS. If AUTH_RATE_LIMIT_COUNT is set, then
# this limit only applies to unauthenticated requests. If this number of
# requests is exceeded within the time interval, the response will be
# 429 Too Many Requests. If this setting is not explicity set, it will default
# to the rate_limit_count value from restlib2.
# See https://github.com/bruth/restlib2 for more information.
RATE_LIMIT_COUNT = None

# Integer defining the length of the request rate limiting time interval
# (in seconds). If AUTH_RATE_LIMIT_SECONDS is set, then this interval duration
# only applies to unauthenticated requests. If more than RATE_LIMIT_COUNT
# requests are received within this time interval, the response will be
# 429 Too Many Requests. If this setting is not explicity set, it will default
# to the rate_limit_seconds value from restlib2.
# See https://github.com/bruth/restlib2 for more information.
RATE_LIMIT_SECONDS = None

# Integer defining the number of authenticated requests that are allowed in
# any given time window defined by AUTH_RATE_LIMIT_SECONDS. If this
# number of authenticated requests is exceeded within the time interval, the
# response will be 429 Too Many Requests. If this setting is not explicity
# set, it will default to RATE_LIMIT_COUNT.
AUTH_RATE_LIMIT_COUNT = None

# Integer defining the length of the authenticated request rate limiting
# time interval(in seconds). If more than AUTH_RATE_LIMIT_COUNT
# authenticated requests are received within this time interval, the response
# will be 429 Too Many Requests. If this setting is not explicity set, it
# will default to RATE_LIMIT_SECONDS.
AUTH_RATE_LIMIT_SECONDS = None

# Name of the reverseable url to use when constructing query urls in emails
# notifying people that a query has been shared with them.
QUERY_REVERSE_NAME = None

# List/tuple of configuration options for defining resources and URLs for
# ObjectSet classes. This requires django-objectset to be installed.
# See https://github.com/bruth/django-objectset for more information.
OBJECT_SETS = ()

# If true, performs a check on all concepts as to whether it contains any
# orphaned fields. This prevents causing server errors for out of sync
# metadata, but incurs an overhead.
CHECK_ORPHANED_FIELDS = True

# Export cookie settings. The template is required to take one positional
# parameter, the export type, to distinguish itself from other exporter
# cookies. The data is simply a value that is set by the server to denote
# the request has been complete.
EXPORT_COOKIE_NAME_TEMPLATE = 'export-type-{0}'
EXPORT_COOKIE_DATA = 'complete'

# Provides a method for determining whether a field supports stats or not. By
# default, stats are not supported on searchable fields. When this method
# returns True, the stats URL will be included in the Link Header as
# generated in the base field resource. Setting this to None will disable
# stats for all fields.
STATS_CAPABLE = lambda x: not x.searchable

# Time to wait when performing a single count on the stats endpoint.
STATS_COUNT_TIMEOUT = 5
