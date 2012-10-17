class SessionMiddleware(object):
    def process_request(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated():
            return
        session = request.session
        # Ensure the session is created view processing, but only if a cookie
        # had been previously set. This is to prevent creating exorbitant
        # numbers of sessions non-browser clients, such as bots.
        if session.session_key is None:
            if session.test_cookie_worked():
                session.delete_test_cookie()
                request.session.create()
            else:
                session.set_test_cookie()
