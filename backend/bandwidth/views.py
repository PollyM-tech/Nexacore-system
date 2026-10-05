import csv

from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organizations.services import get_user_organization

from . import services


def _filters(request):
    return {
        "date_from": (
            request.query_params.get(
                "date_from"
            )
            or None
        ),

        "date_to": (
            request.query_params.get(
                "date_to"
            )
            or None
        ),

        "router": (
            request.query_params.get(
                "router"
            )
            or None
        ),

        "customer": (
            request.query_params.get(
                "customer"
            )
            or None
        ),
    }


class LiveUsageView(APIView):
    """
    Real-time aggregated PPPoE usage and active
    sessions from the current ISP's routers.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    @extend_schema(
        tags=["bandwidth"],
        summary=(
            "Live PPPoE usage and active sessions"
        ),
    )
    def get(
        self,
        request,
    ):
        organization = get_user_organization(
            request.user
        )

        router_id = (
            request.query_params.get(
                "router"
            )
            or None
        )

        return Response(
            services.live_usage(
                organization,
                router_id,
            )
        )


class SyncBandwidthView(APIView):
    """
    Record a snapshot of current active sessions.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    @extend_schema(
        tags=["bandwidth"],
        summary=(
            "Sync (record) a bandwidth snapshot"
        ),
    )
    def post(
        self,
        request,
    ):
        organization = get_user_organization(
            request.user
        )

        router_id = (
            request.data.get(
                "router"
            )
            or request.query_params.get(
                "router"
            )
            or None
        )

        return Response(
            services.record_snapshot(
                organization,
                router_id,
            )
        )


class ConsumptionSummaryView(APIView):
    """
    Today, last seven days and last thirty days
    bandwidth totals.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    @extend_schema(
        tags=["bandwidth"],
        summary="Consumption summary cards",
    )
    def get(
        self,
        request,
    ):
        organization = get_user_organization(
            request.user
        )

        return Response(
            {
                **services.consumption_summary(
                    organization
                ),

                "weekly": (
                    services.weekly_consumption(
                        organization
                    )
                ),
            }
        )


class UsageLogsView(APIView):
    """
    Historical usage logs with date, router and
    customer filters.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    @extend_schema(
        tags=["bandwidth"],
        summary="Historical usage logs",
    )
    def get(
        self,
        request,
    ):
        organization = get_user_organization(
            request.user
        )

        return Response(
            services.usage_logs(
                organization,
                _filters(request),
            )
        )


class TopUsersView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    @extend_schema(
        tags=["bandwidth"],
        summary="Top 50 users by consumption",
    )
    def get(
        self,
        request,
    ):
        organization = get_user_organization(
            request.user
        )

        return Response(
            {
                "results": (
                    services.top_users(
                        organization,
                        _filters(request),
                    )
                )
            }
        )


class RouterSummariesView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    @extend_schema(
        tags=["bandwidth"],
        summary=(
            "Per-router consumption summaries"
        ),
    )
    def get(
        self,
        request,
    ):
        organization = get_user_organization(
            request.user
        )

        return Response(
            {
                "results": (
                    services.router_summaries(
                        organization,
                        _filters(request),
                    )
                )
            }
        )


class ExportUsageView(APIView):
    """
    Export organization-scoped historical usage
    logs as CSV.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    @extend_schema(
        tags=["bandwidth"],
        summary="Export usage logs as CSV",
    )
    def get(
        self,
        request,
    ):
        organization = get_user_organization(
            request.user
        )

        data = services.usage_logs(
            organization,
            _filters(request),
            limit=100000,
        )

        response = HttpResponse(
            content_type="text/csv"
        )

        response[
            "Content-Disposition"
        ] = (
            'attachment; '
            'filename="bandwidth_usage.csv"'
        )

        writer = csv.writer(
            response
        )

        writer.writerow(
            [
                "Date",
                "PPPoE User ID",
                "Customer Name",
                "Upload (bytes)",
                "Download (bytes)",
                "Total Combined (bytes)",
                "Session Uptime",
                "Router Source",
            ]
        )

        for row in data["results"]:
            writer.writerow(
                [
                    row["date"],
                    row["pppoe_id"],
                    row["customer_name"],
                    row["upload_bytes"],
                    row["download_bytes"],
                    row["total_bytes"],
                    row["uptime"],
                    row["router"],
                ]
            )

        return response