# Inspired by http://code.activestate.com/recipes/576567/
import time

class cache_queue_context(object):
    "A context manager for queuing operations per key via memcached"

    poll_interval = 0.005 # in seconds

    def __init__(self, client, key_prefix):
        self.client = client
        self.key_prefix = key_prefix

        self.queue_push_key = self.key_prefix + "-push"
        self.queue_wait_key = self.key_prefix + "-wait"

    def __enter__(self):
        # initialize the queues if needed
        self.client.add(self.queue_push_key, '1')
        self.client.add(self.queue_wait_key, '1')

        # take a number
        index = self.client.incr(self.queue_push_key) - 1

        # poll the queue until your number comes up
        while True:
            idx = int(self.client.get(self.queue_wait_key)) # int() is critical!!!
            if not idx < index:
                break
            time.sleep(self.poll_interval)
        return

    def __exit__(self, exc_type, exc_val, exc_tb):
        # advance the queue
        self.client.incr(self.queue_wait_key)
        return False


class session_queue_context(cache_queue_context):
    "Thin wrapper for handling session data since it could be stale as well."
    def __init__(self, session, *args, **kwargs):
        self.session = session
        super(session_queue_context, self).__init__(*args, **kwargs)

    def __enter__(self):
        super(session_queue_context, self).__enter__()
        del self.session._session_cache

    def __exit__(self, *args, **kwargs):
        self.session.save()
        self.session.modified = False
        return super(session_queue_context, self).__exit__(*args, **kwargs)
