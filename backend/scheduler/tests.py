from django.contrib.auth import get_user_model
from django.test import TestCase
from django_q.models import Schedule
from rest_framework.test import (
    APIRequestFactory,
    force_authenticate,
)

from auditlog.models import AuditLog
from organizations.models import (
    Organization,
    OrganizationMembership,
)
from scheduler.constants import (
    MONTHLY_BILL_TASK,
    SCHEDULER_TASKS,
)
from scheduler.views import SchedulerViewSet


User = get_user_model()


class SchedulerRolePermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.organization = Organization.objects.create(
            name="Scheduler Test ISP",
            slug="scheduler-test-isp",
            organization_type="hybrid",
            status="active",
            is_active=True,
        )

        self.owner = self._create_org_user(
            "scheduler_owner",
            "owner",
        )

        self.admin = self._create_org_user(
            "scheduler_admin",
            "admin",
        )

        self.viewer = self._create_org_user(
            "scheduler_viewer",
            "viewer",
        )

        self.superuser = User.objects.create_superuser(
            username="platform_admin",
            email="admin@example.com",
            password="testpass123",
        )

    def _create_org_user(
        self,
        username,
        role,
    ):
        user = User.objects.create_user(
            username=username,
            password="testpass123",
        )

        OrganizationMembership.objects.create(
            organization=self.organization,
            user=user,
            role=role,
            is_active=True,
        )

        return user

    def _request(
        self,
        method,
        path,
        user,
        data=None,
    ):
        method_func = getattr(
            self.factory,
            method.lower(),
        )

        request = method_func(
            path,
            data=data or {},
            format="json",
        )

        force_authenticate(
            request,
            user=user,
        )

        return request

    def test_viewer_can_list_scheduler_tasks(self):
        view = SchedulerViewSet.as_view(
            {
                "get": "list",
            }
        )

        request = self._request(
            "get",
            "/scheduler/",
            self.viewer,
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_owner_can_list_scheduler_tasks(self):
        view = SchedulerViewSet.as_view(
            {
                "get": "list",
            }
        )

        request = self._request(
            "get",
            "/scheduler/",
            self.owner,
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_org_owner_cannot_create_global_schedule(self):
        view = SchedulerViewSet.as_view(
            {
                "post": "create_task",
            }
        )

        request = self._request(
            "post",
            (
                f"/scheduler/"
                f"{MONTHLY_BILL_TASK}/create/"
            ),
            self.owner,
        )

        response = view(
            request,
            pk=MONTHLY_BILL_TASK,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        cfg = SCHEDULER_TASKS[
            MONTHLY_BILL_TASK
        ]

        self.assertFalse(
            Schedule.objects.filter(
                func=cfg["func"]
            ).exists()
        )

    def test_org_admin_cannot_toggle_global_schedule(self):
        cfg = SCHEDULER_TASKS[
            MONTHLY_BILL_TASK
        ]

        schedule = Schedule.objects.create(
            name=cfg["name"],
            func=cfg["func"],
            schedule_type=(
                cfg["default_schedule_type"]
            ),
            repeats=0,
        )

        view = SchedulerViewSet.as_view(
            {
                "post": "toggle_task",
            }
        )

        request = self._request(
            "post",
            (
                f"/scheduler/"
                f"{MONTHLY_BILL_TASK}/toggle/"
            ),
            self.admin,
            {
                "status": "on",
                "day_of_month": 1,
            },
        )

        response = view(
            request,
            pk=MONTHLY_BILL_TASK,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        schedule.refresh_from_db()

        self.assertEqual(
            schedule.repeats,
            0,
        )

    def test_superuser_can_create_global_schedule(self):
        view = SchedulerViewSet.as_view(
            {
                "post": "create_task",
            }
        )

        request = self._request(
            "post",
            (
                f"/scheduler/"
                f"{MONTHLY_BILL_TASK}/create/"
            ),
            self.superuser,
        )

        response = view(
            request,
            pk=MONTHLY_BILL_TASK,
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        cfg = SCHEDULER_TASKS[
            MONTHLY_BILL_TASK
        ]

        self.assertTrue(
            Schedule.objects.filter(
                func=cfg["func"]
            ).exists()
        )

    def test_superuser_can_toggle_global_schedule(self):
        cfg = SCHEDULER_TASKS[
            MONTHLY_BILL_TASK
        ]

        schedule = Schedule.objects.create(
            name=cfg["name"],
            func=cfg["func"],
            schedule_type=(
                cfg["default_schedule_type"]
            ),
            repeats=0,
        )

        view = SchedulerViewSet.as_view(
            {
                "post": "toggle_task",
            }
        )

        request = self._request(
            "post",
            (
                f"/scheduler/"
                f"{MONTHLY_BILL_TASK}/toggle/"
            ),
            self.superuser,
            {
                "status": "on",
                "day_of_month": 1,
            },
        )

        response = view(
            request,
            pk=MONTHLY_BILL_TASK,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        schedule.refresh_from_db()

        self.assertEqual(
            schedule.repeats,
            -1,
        )

        self.assertEqual(
            schedule.schedule_type,
            "M",
        )

        self.assertIsNotNone(
            schedule.next_run
        )

    def test_superuser_can_delete_global_schedule(self):
        cfg = SCHEDULER_TASKS[
            MONTHLY_BILL_TASK
        ]

        schedule = Schedule.objects.create(
            name=cfg["name"],
            func=cfg["func"],
            schedule_type=(
                cfg["default_schedule_type"]
            ),
            repeats=0,
        )

        view = SchedulerViewSet.as_view(
            {
                "post": "delete_task",
            }
        )

        request = self._request(
            "post",
            (
                f"/scheduler/"
                f"{MONTHLY_BILL_TASK}/delete/"
            ),
            self.superuser,
        )

        response = view(
            request,
            pk=MONTHLY_BILL_TASK,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            Schedule.objects.filter(
                pk=schedule.pk
            ).exists()
        )


class SchedulerAuditLogTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.superuser = User.objects.create_superuser(
            username="scheduler_audit_admin",
            email="scheduler-audit@example.com",
            password="testpass123",
        )

    def _request(
        self,
        method,
        path,
        data=None,
    ):
        method_func = getattr(
            self.factory,
            method.lower(),
        )

        request = method_func(
            path,
            data=data or {},
            format="json",
        )

        force_authenticate(
            request,
            user=self.superuser,
        )

        return request

    def test_schedule_creation_creates_platform_audit_log(
        self,
    ):
        view = SchedulerViewSet.as_view(
            {
                "post": "create_task",
            }
        )

        request = self._request(
            "post",
            (
                f"/scheduler/"
                f"{MONTHLY_BILL_TASK}/create/"
            ),
        )

        response = view(
            request,
            pk=MONTHLY_BILL_TASK,
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        log = AuditLog.objects.get(
            action="scheduler.task_created",
            resource_id=MONTHLY_BILL_TASK,
        )

        self.assertIsNone(
            log.organization
        )

        self.assertEqual(
            log.user,
            self.superuser,
        )

        self.assertEqual(
            log.actor_role,
            "platform_admin",
        )

        self.assertEqual(
            log.metadata["task_id"],
            MONTHLY_BILL_TASK,
        )

        self.assertEqual(
            log.metadata["schedule"][
                "repeats"
            ],
            0,
        )

    def test_schedule_toggle_creates_platform_audit_log(
        self,
    ):
        cfg = SCHEDULER_TASKS[
            MONTHLY_BILL_TASK
        ]

        Schedule.objects.create(
            name=cfg["name"],
            func=cfg["func"],
            schedule_type=(
                cfg["default_schedule_type"]
            ),
            repeats=0,
        )

        view = SchedulerViewSet.as_view(
            {
                "post": "toggle_task",
            }
        )

        request = self._request(
            "post",
            (
                f"/scheduler/"
                f"{MONTHLY_BILL_TASK}/toggle/"
            ),
            {
                "status": "on",
                "day_of_month": 1,
            },
        )

        response = view(
            request,
            pk=MONTHLY_BILL_TASK,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        log = AuditLog.objects.get(
            action="scheduler.task_enabled",
            resource_id=MONTHLY_BILL_TASK,
        )

        self.assertIsNone(
            log.organization
        )

        self.assertEqual(
            log.user,
            self.superuser,
        )

        self.assertEqual(
            log.metadata["before"][
                "repeats"
            ],
            0,
        )

        self.assertEqual(
            log.metadata["after"][
                "repeats"
            ],
            -1,
        )

        self.assertEqual(
            log.metadata["after"][
                "schedule_type"
            ],
            "M",
        )

    def test_schedule_delete_creates_platform_audit_log(
        self,
    ):
        cfg = SCHEDULER_TASKS[
            MONTHLY_BILL_TASK
        ]

        schedule = Schedule.objects.create(
            name=cfg["name"],
            func=cfg["func"],
            schedule_type=(
                cfg["default_schedule_type"]
            ),
            repeats=0,
        )

        schedule_id = schedule.pk

        view = SchedulerViewSet.as_view(
            {
                "post": "delete_task",
            }
        )

        request = self._request(
            "post",
            (
                f"/scheduler/"
                f"{MONTHLY_BILL_TASK}/delete/"
            ),
        )

        response = view(
            request,
            pk=MONTHLY_BILL_TASK,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        log = AuditLog.objects.get(
            action="scheduler.task_deleted",
            resource_id=MONTHLY_BILL_TASK,
        )

        self.assertIsNone(
            log.organization
        )

        self.assertEqual(
            log.user,
            self.superuser,
        )

        self.assertEqual(
            log.actor_role,
            "platform_admin",
        )

        self.assertEqual(
            log.metadata["before"]["id"],
            schedule_id,
        )

        self.assertEqual(
            log.metadata["before"][
                "repeats"
            ],
            0,
        )