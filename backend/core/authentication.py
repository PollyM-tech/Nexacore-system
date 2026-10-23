from auth_kit.authentication import JWTCookieAuthentication
from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS


def enforce_csrf(request):
    check = CSRFCheck(lambda req: None)
    check.process_request(request)
    if check.process_view(request, None, (), {}):
        raise PermissionDenied("CSRF verification failed. Reload the page and try again.")


class StaffCookieAuthentication(JWTCookieAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result and request.method not in SAFE_METHODS and not request.headers.get("Authorization"):
            enforce_csrf(request)
        return result


