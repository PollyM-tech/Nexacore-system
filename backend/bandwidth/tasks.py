"""
Background tasks for historical bandwidth snapshots.

The scheduled job runs without an authenticated user, so it intentionally
loops through every active organization and records each ISP independently.
"""

import logging


logger = logging.getLogger(__name__)


SNAPSHOT_FUNC = (
    "bandwidth.tasks.record_snapshot_job"
)

SNAPSHOT_SCHEDULE_NAME = (
    "Bandwidth Snapshot"
)

SNAPSHOT_MINUTES = 15


def record_snapshot_job():
    """
    Record bandwidth snapshots for every active organization.

    Failure in one ISP must not prevent other organizations from
    being processed.
    """

    from organizations.models import Organization

    from .services import record_snapshot

    organizations = (
        Organization.objects
        .filter(
            is_active=True,
            status="active",
        )
        .order_by("id")
    )

    total_recorded = 0
    processed = 0
    failed = 0

    results = []

    for organization in organizations:
        try:
            result = record_snapshot(
                organization,
                None,
            )

            recorded = result.get(
                "recorded",
                0,
            )

            total_recorded += recorded
            processed += 1

            results.append(
                {
                    "organization_id": (
                        organization.id
                    ),
                    "organization": (
                        organization.name
                    ),
                    "recorded": recorded,
                    "status": "ok",
                }
            )

        except Exception as exc:
            failed += 1

            logger.exception(
                "Bandwidth snapshot failed "
                "for organization %s",
                organization.id,
            )

            results.append(
                {
                    "organization_id": (
                        organization.id
                    ),
                    "organization": (
                        organization.name
                    ),
                    "recorded": 0,
                    "status": "error",
                    "error": str(exc),
                }
            )

    return {
        "status": "ok",
        "organizations_processed": processed,
        "organizations_failed": failed,
        "recorded": total_recorded,
        "results": results,
    }


def ensure_snapshot_schedule():
    """
    Idempotently register the recurring bandwidth
    snapshot schedule.
    """

    try:
        from django_q.models import Schedule

    except Exception:
        return

    Schedule.objects.get_or_create(
        func=SNAPSHOT_FUNC,
        defaults={
            "name": SNAPSHOT_SCHEDULE_NAME,
            "schedule_type": Schedule.MINUTES,
            "minutes": SNAPSHOT_MINUTES,
            "repeats": -1,
        },
    )