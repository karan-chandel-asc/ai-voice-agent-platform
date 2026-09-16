class RequestLoggerMiddleware:
    """Log public Deskline opens for outreach (home + login)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            from monitoring.services import record_visit

            record_visit(request)
        except Exception:
            # Never break the page for analytics.
            pass
        return response
