# Inspired by http://code.activestate.com/recipes/576567/

import time
from django.core.cache import get_cache, DEFAULT_CACHE_ALIAS

class cache_queue(object):
    "A context manager for queuing Django cache operations."

    poll_interval = 0.005 # in seconds

    def __init__(self, key_prefix='', backend=DEFAULT_CACHE_ALIAS):
        self.cache = get_cache(backend)
        self.key_prefix = key_prefix

        self.queue_push_key = self.key_prefix + "-push"
        self.queue_wait_key = self.key_prefix + "-wait"

    def __enter__(self):
        # initialize the queues if needed
        self.cache.add(self.queue_push_key, 1)
        self.cache.add(self.queue_wait_key, 1)

        # take a number
        index = self.cache.incr(self.queue_push_key) - 1

        # poll the queue until your number comes up
        while True:
            idx = int(self.cache.get(self.queue_wait_key)) # int() is critical!!!
            if not idx < index:
                break
            time.sleep(self.poll_interval)

    def __exit__(self, exc_type, exc_val, exc_tb):
        # advance the queue
        self.cache.incr(self.queue_wait_key)

class session_queue(cache_queue):
    "Thin wrapper for queueing session modifications"
    def __init__(self, session, key_prefix='', backend=DEFAULT_CACHE_ALIAS):
        self.session = session
        key_prefix = key_prefix + session.session_key
        super(session_queue, self).__init__(key_prefix, backend)

    def __enter__(self):
        super(session_queue, self).__enter__()
        # session cache is lazily loaded, thus the cache will only be loaded
        # if it has been accessed in some way. we must delete the old cache so
        # it is refreshed upon next access. note, the implication of this is
        # that any prior changes to the session will be thrown out, thus any
        # upstream modifications (e.g. process_request middleware) must save
        # the session ahead of time in a similiar fashion.
        if hasattr(self.session, '_session_cache'):
            delattr(self.session, '_session_cache')

    def __exit__(self, *args, **kwargs):
        # an explicit must occur here to ensure requests in the queue
        # have access to the updated session state. it is important that
        # all components of the session that are sensitive to this context's
        # changes are within the `with` block that. note that
        # SessionMiddleware does still call `save` in `process_response`.
        if self.session.modified:
            self.session.save()
        super(session_queue, self).__exit__(*args, **kwargs)

