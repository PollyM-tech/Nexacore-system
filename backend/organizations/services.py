from rest_framework.exceptions import PermissionDenied

from .models import OrganizationMembership


def get_user_organization(user):
    """
    Return the active organization for the logged-in staff user.

    For now Lintech assumes one active organization per user during normal
    operation. We can add an organization switcher later for multi-org staff.
    """
    if not user or not user.is_authenticated:
        raise PermissionDenied("Authentication is required.")

    membership = (
        OrganizationMembership.objects
        .select_related("organization")
        .filter(
            user=user,
            is_active=True,
            organization__is_active=True,
        )
        .first()
    )

    if not membership:
        raise PermissionDenied(
            "Your account is not assigned to an active organization."
        )

    return membership.organization