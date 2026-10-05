"""
Live PPPoE usage parsing directly from active RouterOS API connections.

All router/customer queries are organization-scoped so one ISP can never
receive another ISP's live network information.

Router failures are best-effort: an unreachable router is skipped rather
than causing the entire API request to fail.
"""

import time

from mikrotik.models import MikrotikRouter, RouterInfo
from mikrotik.service.connection import MikrotikConnection


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def customer_map(organization):
    """
    Map (router_id, lowercased PPPoE username) to customer metadata.

    Including router_id avoids collisions when identical PPPoE usernames
    exist on different routers.
    """

    result = {}

    queryset = (
        RouterInfo.objects
        .filter(
            customer__organization=organization,
            router__organization=organization,
        )
        .select_related(
            "customer",
            "customer__package",
            "router",
        )
    )

    for info in queryset:
        customer = info.customer

        if not customer:
            continue

        key = (
            info.router_id,
            info.pppoe_name.lower(),
        )

        result[key] = {
            "customer_id": customer.customer_id,
            "customer_name": customer.customer_name,
            "package": (
                customer.package.name
                if customer.package_id
                else None
            ),
            "billing_status": customer.customer_status,
            "balance": float(customer.balance or 0),
        }

    return result


def _collect_router(router, cust_map):
    """
    Return (sessions, connected) for one router.

    Router connection failures never escape this function.
    """

    try:
        conn = MikrotikConnection(
            host=router.host,
            port=router.port,
            username=router.username,
            password=router.password,
        )

        if not conn.api:
            return [], False

        active = (
            conn.api
            .get_resource("/ppp/active")
            .get()
        )

        try:
            secrets = (
                conn.api
                .get_resource("/ppp/secret")
                .get()
            )

            profiles = {
                secret.get("name", "").lower():
                    secret.get("profile", "")
                for secret in secrets
            }

        except Exception:
            profiles = {}

        sessions = []

        for active_session in active:
            name = active_session.get(
                "name",
                "",
            )

            key = (
                router.id,
                name.lower(),
            )

            meta = cust_map.get(
                key,
                {},
            )

            sessions.append(
                {
                    "pppoe_id": name,
                    "customer_id": meta.get(
                        "customer_id"
                    ),
                    "customer_name": (
                        meta.get("customer_name")
                        or name
                    ),
                    "address": active_session.get(
                        "address",
                        "",
                    ),
                    "caller_id": active_session.get(
                        "caller-id",
                        "",
                    ),
                    "uptime": active_session.get(
                        "uptime",
                        "",
                    ),

                    # MikroTik bytes-out is traffic sent
                    # TO the customer (download).
                    "download_bytes": _to_int(
                        active_session.get(
                            "bytes-out"
                        )
                    ),

                    # MikroTik bytes-in is traffic received
                    # FROM the customer (upload).
                    "upload_bytes": _to_int(
                        active_session.get(
                            "bytes-in"
                        )
                    ),

                    "profile": (
                        meta.get("package")
                        or profiles.get(
                            name.lower(),
                            "",
                        )
                    ),

                    "billing_status": meta.get(
                        "billing_status",
                        "unknown",
                    ),

                    "balance": meta.get(
                        "balance",
                        0,
                    ),

                    "router": router.name,
                    "router_id": router.id,
                }
            )

        return sessions, True

    except Exception:
        return [], False


def live_usage(
    organization,
    router_id=None,
):
    """
    Aggregate live PPPoE sessions across an organization's active routers.

    Byte values are cumulative RouterOS session counters. Client-side speed
    calculations can derive rates from the difference between successive
    polls.
    """

    routers = (
        MikrotikRouter.objects
        .filter(
            organization=organization,
            is_active=True,
        )
    )

    if router_id:
        routers = routers.filter(
            id=router_id
        )

    cust_map = customer_map(
        organization
    )

    sessions = []
    connected = False

    for router in routers:
        router_sessions, ok = _collect_router(
            router,
            cust_map,
        )

        connected = connected or ok

        sessions.extend(
            router_sessions
        )

    return {
        "router_connected": connected,
        "router_count": routers.count(),
        "online_clients": len(sessions),

        "total_download_bytes": sum(
            session["download_bytes"]
            for session in sessions
        ),

        "total_upload_bytes": sum(
            session["upload_bytes"]
            for session in sessions
        ),

        "timestamp": int(
            time.time() * 1000
        ),

        "sessions": sessions,
    }