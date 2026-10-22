from rest_framework.permissions import BasePermission


class IsPlatformAdmin(BasePermission):
    message = "Platform administrator access is required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
