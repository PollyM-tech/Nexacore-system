from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organizations.permissions import (
    READ_ONLY_ROLES,
    HasOrganizationRole,
)
from organizations.services import (
    get_user_organization,
)

from .services import ReportService


class DashboardReportView(APIView):
    """
    Organization-scoped dashboard summary.
    """

    permission_classes = [
        IsAuthenticated,
        HasOrganizationRole,
    ]

    role_permissions = {
        "get": READ_ONLY_ROLES,
    }

    @extend_schema(
        tags=["reports"],
        summary="Admin dashboard summary",
    )
    def get(
        self,
        request,
    ):
        organization = get_user_organization(
            request.user
        )

        return Response(
            ReportService.dashboard_summary(
                organization
            )
        )