from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from organizations.permissions import (
    READ_ONLY_ROLES,
    HasOrganizationRole,
)
from organizations.services import (
    get_user_organization,
)

from radius.services import (
    RadiusAccountingService,
    RadiusProvisioningError,
)


class RadiusSessionViewSet(viewsets.ViewSet):
    """
    Read-only API for FreeRADIUS accounting sessions.

    All results are scoped to the authenticated user's
    organization.
    """

    permission_classes = [
        IsAuthenticated,
        HasOrganizationRole,
    ]

    role_permissions = {
        "list": READ_ONLY_ROLES,
        "active": READ_ONLY_ROLES,
        "customer_sessions": READ_ONLY_ROLES,
        "customer_summary": READ_ONLY_ROLES,
    }

    def get_organization(self):
        return get_user_organization(
            self.request.user
        )

    @staticmethod
    def _get_limit(request):
        """
        Optional result limit.

        Defaults to 100 and is capped at 500.
        """
        raw_limit = request.query_params.get(
            "limit",
            100,
        )

        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            limit = 100

        if limit < 1:
            limit = 1

        return min(
            limit,
            500,
        )

    def list(
        self,
        request,
    ):
        """
        GET /api/radius/sessions/

        Return RADIUS accounting history for
        customers belonging to the organization.
        """
        organization = (
            self.get_organization()
        )

        limit = self._get_limit(
            request
        )

        sessions = (
            RadiusAccountingService
            .organization_session_data(
                organization,
                active_only=False,
            )
        )

        sessions = sessions[:limit]

        return Response(
            {
                "count": len(sessions),
                "results": sessions,
            },
            status=status.HTTP_200_OK,
        )

    def active(
        self,
        request,
    ):
        """
        GET /api/radius/sessions/active/

        Return currently active RADIUS sessions.
        """
        organization = (
            self.get_organization()
        )

        limit = self._get_limit(
            request
        )

        sessions = (
            RadiusAccountingService
            .organization_session_data(
                organization,
                active_only=True,
            )
        )

        sessions = sessions[:limit]

        return Response(
            {
                "count": len(sessions),
                "results": sessions,
            },
            status=status.HTTP_200_OK,
        )

    def customer_sessions(
        self,
        request,
        customer_id=None,
    ):
        """
        GET
        /api/radius/customers/<customer_id>/sessions/

        Return accounting history for one customer.
        """
        organization = (
            self.get_organization()
        )

        limit = self._get_limit(
            request
        )

        try:
            sessions = (
                RadiusAccountingService
                .customer_session_data(
                    organization,
                    customer_id,
                )
            )

        except RadiusProvisioningError as exc:
            return Response(
                {
                    "status": "error",
                    "message": str(exc),
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )

        sessions = sessions[:limit]

        return Response(
            {
                "customer_id": customer_id,
                "count": len(sessions),
                "results": sessions,
            },
            status=status.HTTP_200_OK,
        )

    def customer_summary(
        self,
        request,
        customer_id=None,
    ):
        """
        GET
        /api/radius/customers/<customer_id>/summary/

        Return online state, latest session and
        historical totals for one customer.
        """
        organization = (
            self.get_organization()
        )

        try:
            customer = (
                RadiusAccountingService
                ._get_customer(
                    organization,
                    customer_id,
                )
            )

            totals = (
                RadiusAccountingService
                .customer_totals(
                    organization,
                    customer_id,
                )
            )

            online = (
                RadiusAccountingService
                .customer_is_online(
                    organization,
                    customer_id,
                )
            )

            latest = (
                RadiusAccountingService
                .latest_customer_session(
                    organization,
                    customer_id,
                )
            )

        except RadiusProvisioningError as exc:
            return Response(
                {
                    "status": "error",
                    "message": str(exc),
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )

        latest_session = None

        if latest:
            latest_session = (
                RadiusAccountingService
                .session_to_dict(
                    latest,
                    customer,
                )
            )

        return Response(
            {
                "customer_id": (
                    customer.customer_id
                ),
                "customer_name": (
                    customer.customer_name
                ),
                "online": online,
                "totals": totals,
                "latest_session": (
                    latest_session
                ),
            },
            status=status.HTTP_200_OK,
        )