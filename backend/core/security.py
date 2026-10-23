"""Cookie authentication safeguards and deliberately closed public signup."""
from auth_kit.views import LoginView, LogoutView
from auth_kit.views.jwt import RefreshViewWithCookieSupport
from django.conf import settings
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, BasePermission, SAFE_METHODS
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView


from .authentication import enforce_csrf


class RequireCsrf(BasePermission):
    def has_permission(self, request, view):
        if request.method not in SAFE_METHODS:
            enforce_csrf(request)
        return True


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class StaffLoginView(LoginView):
    permission_classes = [AllowAny, RequireCsrf]
    throttle_classes = [LoginThrottle]


class StaffRefreshView(RefreshViewWithCookieSupport):
    permission_classes = [AllowAny, RequireCsrf]
    throttle_classes = [LoginThrottle]


class StaffLogoutView(LogoutView):
    def initial(self, request, *args, **kwargs):
        # Auth Kit mutates request.data during initial(), which crashes on form
        # QueryDicts. Its JWT logout already reads the refresh cookie directly.
        # Keep standard DRF auth/permissions (including cookie CSRF) without that mutation.
        APIView.initial(self, request, *args, **kwargs)


class ClosedRegistrationView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raise PermissionDenied("Public registration is disabled. Contact your ISP administrator.")


@never_cache
def csrf_cookie(request):
    # The token is public; the browser must echo it with the matching cookie.
    return JsonResponse({"csrfToken": get_token(request)})


@never_cache
def health(request):
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok", "release": settings.LINTECH_RELEASE})
