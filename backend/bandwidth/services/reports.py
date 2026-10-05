"""
Historical bandwidth analytics derived from persisted BandwidthSample rows.

Every public service function requires an organization so historical data
cannot cross ISP boundaries.
"""

from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from mikrotik.models import (
    MikrotikRouter,
    RouterInfo,
)

from ..models import BandwidthSample
from .live import live_usage


def _i(value):
    return int(
        value or 0
    )


def record_snapshot(
    organization,
    router_id=None,
):
    """
    Capture current active PPPoE sessions as BandwidthSample rows.

    Every stored sample receives permanent organization ownership.
    """

    data = live_usage(
        organization,
        router_id,
    )

    router_infos = (
        RouterInfo.objects
        .filter(
            customer__organization=organization,
            router__organization=organization,
        )
        .select_related(
            "customer",
            "router",
        )
    )

    info_map = {
        (
            info.router_id,
            info.pppoe_name.lower(),
        ): info
        for info in router_infos
    }

    routers = (
        MikrotikRouter.objects
        .filter(
            organization=organization
        )
    )

    router_map = {
        router.id: router
        for router in routers
    }

    samples = []

    for session in data["sessions"]:
        router_id_value = session[
            "router_id"
        ]

        key = (
            router_id_value,
            session["pppoe_id"].lower(),
        )

        info = info_map.get(
            key
        )

        router = router_map.get(
            router_id_value
        )

        samples.append(
            BandwidthSample(
                organization=organization,

                customer=(
                    info.customer
                    if info
                    else None
                ),

                router=router,

                pppoe_id=session[
                    "pppoe_id"
                ],

                customer_name=session[
                    "customer_name"
                ],

                upload_bytes=session[
                    "upload_bytes"
                ],

                download_bytes=session[
                    "download_bytes"
                ],

                uptime=session[
                    "uptime"
                ],
            )
        )

    if samples:
        BandwidthSample.objects.bulk_create(
            samples
        )

    return {
        "status": "ok",
        "recorded": len(samples),
        "router_connected": data[
            "router_connected"
        ],
    }


def _window(
    organization,
    start_date,
):
    aggregate = (
        BandwidthSample.objects
        .filter(
            organization=organization,
            created_at__date__gte=start_date,
        )
        .aggregate(
            upload=Sum(
                "upload_bytes"
            ),
            download=Sum(
                "download_bytes"
            ),
        )
    )

    upload = _i(
        aggregate["upload"]
    )

    download = _i(
        aggregate["download"]
    )

    return {
        "upload_bytes": upload,
        "download_bytes": download,
        "total_bytes": (
            upload + download
        ),
    }


def consumption_summary(
    organization,
):
    today = timezone.now().date()

    return {
        "today": _window(
            organization,
            today,
        ),

        "last_7_days": _window(
            organization,
            today - timedelta(days=6),
        ),

        "last_30_days": _window(
            organization,
            today - timedelta(days=29),
        ),
    }


def _filtered(
    organization,
    filters,
):
    queryset = (
        BandwidthSample.objects
        .filter(
            organization=organization
        )
        .select_related(
            "router",
            "customer",
        )
    )

    if filters.get("date_from"):
        queryset = queryset.filter(
            created_at__date__gte=filters[
                "date_from"
            ]
        )

    if filters.get("date_to"):
        queryset = queryset.filter(
            created_at__date__lte=filters[
                "date_to"
            ]
        )

    if filters.get("router"):
        queryset = queryset.filter(
            router_id=filters[
                "router"
            ]
        )

    if filters.get("customer"):
        queryset = queryset.filter(
            customer__customer_id=filters[
                "customer"
            ]
        )

    return queryset


def usage_logs(
    organization,
    filters,
    limit=1000,
):
    queryset = _filtered(
        organization,
        filters,
    )

    totals = queryset.aggregate(
        upload=Sum(
            "upload_bytes"
        ),
        download=Sum(
            "download_bytes"
        ),
    )

    rows = [
        {
            "id": sample.id,

            "date": (
                sample.created_at
                .isoformat()
            ),

            "pppoe_id": sample.pppoe_id,

            "customer_name": (
                sample.customer_name
            ),

            "upload_bytes": (
                sample.upload_bytes
            ),

            "download_bytes": (
                sample.download_bytes
            ),

            "total_bytes": (
                sample.upload_bytes
                + sample.download_bytes
            ),

            "uptime": sample.uptime,

            "router": (
                sample.router.name
                if sample.router
                else "—"
            ),
        }

        for sample in queryset.order_by(
            "-created_at"
        )[:limit]
    ]

    upload = _i(
        totals["upload"]
    )

    download = _i(
        totals["download"]
    )

    return {
        "results": rows,

        "totals": {
            "upload_bytes": upload,
            "download_bytes": download,
            "total_bytes": (
                upload + download
            ),
        },
    }


def top_users(
    organization,
    filters,
    limit=50,
):
    queryset = _filtered(
        organization,
        filters,
    )

    rows = (
        queryset
        .values(
            "pppoe_id",
            "customer_name",
        )
        .annotate(
            upload_bytes=Sum(
                "upload_bytes"
            ),
            download_bytes=Sum(
                "download_bytes"
            ),
            sessions=Count(
                "id"
            ),
        )
        .order_by(
            "-download_bytes"
        )[:limit]
    )

    return [
        {
            "pppoe_id": row[
                "pppoe_id"
            ],

            "customer_name": row[
                "customer_name"
            ],

            "upload_bytes": _i(
                row["upload_bytes"]
            ),

            "download_bytes": _i(
                row["download_bytes"]
            ),

            "total_bytes": (
                _i(row["upload_bytes"])
                + _i(row["download_bytes"])
            ),

            "sessions": row[
                "sessions"
            ],
        }

        for row in rows
    ]


def router_summaries(
    organization,
    filters,
):
    queryset = _filtered(
        organization,
        filters,
    )

    rows = (
        queryset
        .values(
            "router__name"
        )
        .annotate(
            upload_bytes=Sum(
                "upload_bytes"
            ),
            download_bytes=Sum(
                "download_bytes"
            ),
            sessions=Count(
                "id"
            ),
            clients=Count(
                "pppoe_id",
                distinct=True,
            ),
        )
        .order_by(
            "-download_bytes"
        )
    )

    return [
        {
            "router": (
                row["router__name"]
                or "—"
            ),

            "upload_bytes": _i(
                row["upload_bytes"]
            ),

            "download_bytes": _i(
                row["download_bytes"]
            ),

            "total_bytes": (
                _i(row["upload_bytes"])
                + _i(row["download_bytes"])
            ),

            "sessions": row[
                "sessions"
            ],

            "clients": row[
                "clients"
            ],
        }

        for row in rows
    ]


def weekly_consumption(
    organization,
):
    """
    Per-day upload/download totals for the last seven days.
    """

    today = timezone.now().date()

    rows = []

    for offset in range(
        6,
        -1,
        -1,
    ):
        day = (
            today
            - timedelta(days=offset)
        )

        aggregate = (
            BandwidthSample.objects
            .filter(
                organization=organization,
                created_at__date=day,
            )
            .aggregate(
                upload=Sum(
                    "upload_bytes"
                ),
                download=Sum(
                    "download_bytes"
                ),
            )
        )

        rows.append(
            {
                "date": day.isoformat(),

                "label": day.strftime(
                    "%a"
                ),

                "download_bytes": _i(
                    aggregate[
                        "download"
                    ]
                ),

                "upload_bytes": _i(
                    aggregate[
                        "upload"
                    ]
                ),
            }
        )

    return rows