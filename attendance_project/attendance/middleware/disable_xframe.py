# attendance/middleware/disable_xframe.py

class DisableXFrameOptionsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/admin/') or request.path.startswith('/admin-dashboard/'):
            response.headers.pop('X-Frame-Options', None)
        return response