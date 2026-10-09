import calendar
import datetime

from django.utils import timezone
from django_q.models import Schedule
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    BasePermission,
    IsAuthenticated,
)
from rest_framework.response import Response

from auditlog.services import AuditService
from organizations.permissions import (
    READ_ONLY_ROLES,
    HasOrganizationRole,
)

from scheduler.constants import (
    BILL_DUE_DISCONNECT_TASK,
    BILLING_DATE_UPDATE_TASK,
    MONTHLY_BILL_TASK,
    PAYMENT_PROVISIONING_RETRY_TASK,
    SCHEDULER_TASKS,
)
from scheduler.schemas import scheduler_schema_view
from scheduler.serializers import (
    SchedulerTaskSerializer,
    SchedulerToggleSerializer,
)


class IsPlatformAdministrator(BasePermission):
    """
    Restrict global scheduler modifications to
    Lintech platform administrators.

    Django-Q schedules are global and are not tied
    to an organization.
    """

    message = (
        "Only a Lintech platform administrator "
        "can modify global scheduler tasks."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and user.is_superuser
        )


def _schedule_audit_snapshot(
    schedule,
):
    """
    Return JSON-safe scheduler information.
    """

    if schedule is None:
        return None

    return {
        "id": schedule.pk,
        "name": schedule.name,
        "func": schedule.func,
        "schedule_type": schedule.schedule_type,
        "repeats": schedule.repeats,
        "next_run": (
            schedule.next_run.isoformat()
            if schedule.next_run
            else None
        ),
    }


def get_next_monthly_run(
    day_of_month,
):
    now = timezone.now()
    today = now.date()

    try:
        max_days = calendar.monthrange(
            today.year,
            today.month,
        )[1]

        target_day = min(
            day_of_month,
            max_days,
        )

        candidate = datetime.datetime(
            today.year,
            today.month,
            target_day,
            0,
            0,
            0,
        )

        candidate = timezone.make_aware(
            candidate,
            timezone.get_current_timezone(),
        )

        if candidate > now:
            return candidate

    except ValueError:
        pass

    if today.month == 12:
        next_month = 1
        next_year = today.year + 1
    else:
        next_month = today.month + 1
        next_year = today.year

    max_days = calendar.monthrange(
        next_year,
        next_month,
    )[1]

    target_day = min(
        day_of_month,
        max_days,
    )

    result = datetime.datetime(
        next_year,
        next_month,
        target_day,
        0,
        0,
        0,
    )

    return timezone.make_aware(
        result,
        timezone.get_current_timezone(),
    )


@scheduler_schema_view
class SchedulerViewSet(
    viewsets.ViewSet
):
    """
    Manage Lintech's global background schedules.

    Schedule records are global Django-Q objects,
    not organization-owned records.
    """

    def get_permissions(self):
        if self.action == "list":
            permission_classes = [
                IsAuthenticated,
                HasOrganizationRole,
            ]

        else:
            permission_classes = [
                IsAuthenticated,
                IsPlatformAdministrator,
            ]

        return [
            permission()
            for permission in permission_classes
        ]

    role_permissions = {
        "list": READ_ONLY_ROLES,
    }

    def list(
        self,
        request,
    ):
        data = []

        for task_id, cfg in SCHEDULER_TASKS.items():
            schedule = (
                Schedule.objects
                .filter(
                    func=cfg["func"]
                )
                .first()
            )

            task_status = "not_created"
            next_run = None
            repeats = None
            schedule_type = None
            day_of_month = None

            if schedule:
                if schedule.repeats == -1:
                    task_status = "on"
                else:
                    task_status = "off"

                next_run = schedule.next_run
                repeats = schedule.repeats
                schedule_type = (
                    schedule.schedule_type
                )

                if (
                    schedule.schedule_type == "M"
                    and schedule.next_run
                ):
                    day_of_month = (
                        schedule.next_run.day
                    )

            data.append(
                {
                    "task_id": task_id,
                    "name": cfg["name"],
                    "func": cfg["func"],
                    "status": task_status,
                    "next_run": next_run,
                    "repeats": repeats,
                    "schedule_type": (
                        schedule_type
                    ),
                    "day_of_month": (
                        day_of_month
                    ),
                }
            )

        serializer = SchedulerTaskSerializer(
            data,
            many=True,
        )

        return Response(
            serializer.data
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="create",
    )
    def create_task(
        self,
        request,
        pk=None,
    ):
        if pk not in SCHEDULER_TASKS:
            return Response(
                {
                    "status": "error",
                    "message": "Invalid task ID",
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        cfg = SCHEDULER_TASKS[pk]

        schedule = (
            Schedule.objects
            .filter(
                func=cfg["func"]
            )
            .first()
        )

        created = False

        if not schedule:
            schedule = Schedule.objects.create(
                name=cfg["name"],
                func=cfg["func"],
                schedule_type=(
                    cfg[
                        "default_schedule_type"
                    ]
                ),
                repeats=0,
                next_run=timezone.now(),
            )

            created = True

        if created:
            AuditService.log(
                organization=None,
                user=request.user,
                request=request,
                action="scheduler.task_created",
                resource_type="Schedule",
                resource_id=pk,
                description=(
                    f"Global scheduler task "
                    f"'{cfg['name']}' created."
                ),
                metadata={
                    "task_id": pk,
                    "schedule": (
                        _schedule_audit_snapshot(
                            schedule
                        )
                    ),
                },
            )

        return Response(
            {
                "status": "success",
                "message": (
                    f"Task '{cfg['name']}' "
                    "schedule record initialized "
                    "(off)"
                ),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="delete",
    )
    def delete_task(
        self,
        request,
        pk=None,
    ):
        if pk not in SCHEDULER_TASKS:
            return Response(
                {
                    "status": "error",
                    "message": "Invalid task ID",
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        cfg = SCHEDULER_TASKS[pk]

        schedule = (
            Schedule.objects
            .filter(
                func=cfg["func"]
            )
            .first()
        )

        if schedule:
            before = _schedule_audit_snapshot(
                schedule
            )

            schedule.delete()

            AuditService.log(
                organization=None,
                user=request.user,
                request=request,
                action="scheduler.task_deleted",
                resource_type="Schedule",
                resource_id=pk,
                description=(
                    f"Global scheduler task "
                    f"'{cfg['name']}' deleted."
                ),
                metadata={
                    "task_id": pk,
                    "before": before,
                },
            )

            return Response(
                {
                    "status": "success",
                    "message": (
                        "Deleted scheduler "
                        f"record for "
                        f"'{cfg['name']}'"
                    ),
                }
            )

        return Response(
            {
                "status": "error",
                "message": (
                    "Task schedule record "
                    "does not exist"
                ),
            },
            status=(
                status.HTTP_404_NOT_FOUND
            ),
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="toggle",
    )
    def toggle_task(
        self,
        request,
        pk=None,
    ):
        if pk not in SCHEDULER_TASKS:
            return Response(
                {
                    "status": "error",
                    "message": "Invalid task ID",
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        serializer = SchedulerToggleSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        cfg = SCHEDULER_TASKS[pk]

        schedule = (
            Schedule.objects
            .filter(
                func=cfg["func"]
            )
            .first()
        )

        if not schedule:
            return Response(
                {
                    "status": "error",
                    "message": (
                        "Task scheduler record "
                        "must be created first "
                        "before toggling."
                    ),
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )

        toggle_status = (
            serializer.validated_data[
                "status"
            ]
        )

        before = _schedule_audit_snapshot(
            schedule
        )

        if toggle_status == "off":
            schedule.repeats = 0

            schedule.save(
                update_fields=[
                    "repeats",
                ]
            )

            AuditService.log(
                organization=None,
                user=request.user,
                request=request,
                action="scheduler.task_disabled",
                resource_type="Schedule",
                resource_id=pk,
                description=(
                    f"Global scheduler task "
                    f"'{cfg['name']}' disabled."
                ),
                metadata={
                    "task_id": pk,
                    "before": before,
                    "after": (
                        _schedule_audit_snapshot(
                            schedule
                        )
                    ),
                },
            )

            return Response(
                {
                    "status": "success",
                    "message": (
                        f"Task '{cfg['name']}' "
                        "is now turned off."
                    ),
                }
            )

        if toggle_status == "on":
            schedule.repeats = -1

            if pk == MONTHLY_BILL_TASK:
                day_of_month = (
                    serializer.validated_data.get(
                        "day_of_month",
                        1,
                    )
                )

                schedule.next_run = (
                    get_next_monthly_run(
                        day_of_month
                    )
                )

                schedule.schedule_type = "M"

            elif pk == BILL_DUE_DISCONNECT_TASK:
                schedule.next_run = (
                    timezone.now()
                    + datetime.timedelta(
                        hours=1
                    )
                )

                schedule.schedule_type = "H"

            elif pk == PAYMENT_PROVISIONING_RETRY_TASK:
                schedule.next_run = (
                    timezone.now()
                    + datetime.timedelta(
                        hours=1
                    )
                )

                schedule.schedule_type = "H"

            elif pk == BILLING_DATE_UPDATE_TASK:
                tomorrow = (
                    timezone.localdate()
                    + datetime.timedelta(
                        days=1
                    )
                )

                next_run = datetime.datetime.combine(
                    tomorrow,
                    datetime.time.min,
                )

                schedule.next_run = (
                    timezone.make_aware(
                        next_run,
                        timezone.get_current_timezone(),
                    )
                )

                schedule.schedule_type = "D"

            schedule.save(
                update_fields=[
                    "repeats",
                    "next_run",
                    "schedule_type",
                ]
            )

            AuditService.log(
                organization=None,
                user=request.user,
                request=request,
                action="scheduler.task_enabled",
                resource_type="Schedule",
                resource_id=pk,
                description=(
                    f"Global scheduler task "
                    f"'{cfg['name']}' enabled."
                ),
                metadata={
                    "task_id": pk,
                    "before": before,
                    "after": (
                        _schedule_audit_snapshot(
                            schedule
                        )
                    ),
                },
            )

            return Response(
                {
                    "status": "success",
                    "message": (
                        f"Task '{cfg['name']}' "
                        "is now turned on. "
                        "Next run scheduled at "
                        f"{schedule.next_run}."
                    ),
                }
            )

        return Response(
            {
                "status": "error",
                "message": (
                    "Invalid scheduler status."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )