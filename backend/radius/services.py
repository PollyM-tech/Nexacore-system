from datetime import timedelta

import re
import secrets
import string

from django.db import transaction
from django.db.models import Count,Q, Sum
from django.utils import timezone

from customers.models import CustomerProfile
from radius.models import RadAcct, RadiusCheck, RadiusReply


class RadiusProvisioningError(Exception):
    """Raised when a customer cannot be provisioned in RADIUS."""


class RadiusProvisioningService:
    PASSWORD_LENGTH = 12

    @classmethod
    def _generate_password(cls):
        alphabet = string.ascii_letters + string.digits

        return "".join(
            secrets.choice(alphabet)
            for _ in range(cls.PASSWORD_LENGTH)
        )

    @staticmethod
    def build_radius_username(customer):
        """
        Build a globally unique RADIUS username.

        Example:
            lintech-demo-test001
        """
        organization_slug = (
            customer.organization.slug
            .strip()
            .lower()
        )

        customer_id = (
            customer.customer_id
            .strip()
            .lower()
        )

        username = (
            f"{organization_slug}-{customer_id}"
        )

        username = re.sub(
            r"[^a-z0-9_.-]+",
            "-",
            username,
        )

        username = re.sub(
            r"-+",
            "-",
            username,
        ).strip("-")

        if not username:
            raise RadiusProvisioningError(
                "Could not generate a valid "
                "RADIUS username."
            )

        if len(username) > 64:
            raise RadiusProvisioningError(
                "Generated RADIUS username "
                "exceeds 64 characters."
            )

        return username

    @staticmethod
    def _mikrotik_rate_limit(speed):
        """
        Convert package speed to MikroTik-Rate-Limit format.

        Examples:
            5Mbps   -> 5M/5M
            10 Mbps -> 10M/10M
            512Kbps -> 512K/512K
            20M     -> 20M/20M
            10M/20M -> 10M/20M
        """
        if not speed:
            raise RadiusProvisioningError(
                "Customer package does not "
                "have a speed configured."
            )

        value = str(speed).strip()

        if "/" in value:
            return value

        compact = (
            value.upper()
            .replace(" ", "")
        )

        compact = compact.replace(
            "MBPS",
            "M",
        )

        compact = compact.replace(
            "KBPS",
            "K",
        )

        compact = compact.replace(
            "GBPS",
            "G",
        )

        if re.fullmatch(
            r"\d+(?:\.\d+)?[KMG]",
            compact,
        ):
            return (
                f"{compact}/{compact}"
            )

        raise RadiusProvisioningError(
            "Unsupported package speed "
            f"format: {speed!r}"
        )

    @classmethod
    def _set_radius_rejected(
        cls,
        username,
    ):
        """
        Ensure the user is rejected by FreeRADIUS.
        """
        reject_rows = list(
            RadiusCheck.objects
            .filter(
                username=username,
                attribute="Auth-Type",
            )
            .order_by("id")
        )

        if reject_rows:
            reject_record = reject_rows[0]

            reject_record.op = ":="
            reject_record.value = "Reject"

            reject_record.save(
                update_fields=[
                    "op",
                    "value",
                ]
            )

            if len(reject_rows) > 1:
                RadiusCheck.objects.filter(
                    id__in=[
                        row.id
                        for row
                        in reject_rows[1:]
                    ]
                ).delete()

        else:
            RadiusCheck.objects.create(
                username=username,
                attribute="Auth-Type",
                op=":=",
                value="Reject",
            )

    @classmethod
    def _remove_radius_rejection(
        cls,
        username,
    ):
        """
        Remove Lintech's explicit RADIUS rejection.
        """
        RadiusCheck.objects.filter(
            username=username,
            attribute="Auth-Type",
            value="Reject",
        ).delete()

    @classmethod
    @transaction.atomic
    def provision_pppoe_customer(
        cls,
        customer,
        password=None,
        reset_password=False,
    ):
        """
        Provision or update a PPPoE customer
        in FreeRADIUS.
        """
        if not isinstance(
            customer,
            CustomerProfile,
        ):
            raise RadiusProvisioningError(
                "customer must be a "
                "CustomerProfile instance."
            )

        customer = (
            CustomerProfile.objects
            .select_for_update()
            .get(
                pk=customer.pk
            )
        )

        organization = (
            customer.organization
        )

        if not organization.is_active:
            raise RadiusProvisioningError(
                "Customer organization "
                "is inactive."
            )

        if customer.package_id is None:
            raise RadiusProvisioningError(
                "Customer does not have "
                "a package."
            )

        package = customer.package

        if not package.is_active:
            raise RadiusProvisioningError(
                "Customer package "
                "is inactive."
            )

        username = (
            cls.build_radius_username(
                customer
            )
        )

        rate_limit = (
            cls._mikrotik_rate_limit(
                package.speed
            )
        )

        password_rows = list(
            RadiusCheck.objects
            .filter(
                username=username,
                attribute=(
                    "Cleartext-Password"
                ),
            )
            .order_by("id")
        )

        created = not password_rows

        if not password_rows:
            radius_password = (
                password
                or cls._generate_password()
            )

            password_record = (
                RadiusCheck.objects.create(
                    username=username,
                    attribute=(
                        "Cleartext-Password"
                    ),
                    op=":=",
                    value=radius_password,
                )
            )

        else:
            password_record = (
                password_rows[0]
            )

            if reset_password:
                radius_password = (
                    password
                    or cls._generate_password()
                )

                password_record.op = ":="
                password_record.value = (
                    radius_password
                )

                password_record.save(
                    update_fields=[
                        "op",
                        "value",
                    ]
                )

            else:
                radius_password = (
                    password_record.value
                )

            if len(password_rows) > 1:
                RadiusCheck.objects.filter(
                    id__in=[
                        row.id
                        for row
                        in password_rows[1:]
                    ]
                ).delete()

        if password_record.op != ":=":
            password_record.op = ":="

            password_record.save(
                update_fields=[
                    "op",
                ]
            )

        rate_rows = list(
            RadiusReply.objects
            .filter(
                username=username,
                attribute=(
                    "Mikrotik-Rate-Limit"
                ),
            )
            .order_by("id")
        )

        if rate_rows:
            rate_record = (
                rate_rows[0]
            )

            rate_record.op = ":="
            rate_record.value = (
                rate_limit
            )

            rate_record.save(
                update_fields=[
                    "op",
                    "value",
                ]
            )

            if len(rate_rows) > 1:
                RadiusReply.objects.filter(
                    id__in=[
                        row.id
                        for row
                        in rate_rows[1:]
                    ]
                ).delete()

        else:
            RadiusReply.objects.create(
                username=username,
                attribute=(
                    "Mikrotik-Rate-Limit"
                ),
                op=":=",
                value=rate_limit,
            )

        # Customer status controls whether
        # RADIUS may authenticate.
        if customer.customer_status == "active":
            cls._remove_radius_rejection(
                username
            )
        else:
            cls._set_radius_rejected(
                username
            )

        return {
            "username": username,
            "password": radius_password,
            "rate_limit": rate_limit,
            "created": created,
        }

    @classmethod
    @transaction.atomic
    def suspend_pppoe_customer(
        cls,
        customer,
    ):
        """
        Prevent future authentication while
        preserving credentials.
        """
        customer = (
            CustomerProfile.objects
            .select_for_update()
            .get(
                pk=customer.pk
            )
        )

        username = (
            cls.build_radius_username(
                customer
            )
        )

        cls._set_radius_rejected(
            username
        )

        return username

    @classmethod
    @transaction.atomic
    def reactivate_pppoe_customer(
        cls,
        customer,
    ):
        """
        Allow authentication again.
        """
        customer = (
            CustomerProfile.objects
            .select_for_update()
            .get(
                pk=customer.pk
            )
        )

        username = (
            cls.build_radius_username(
                customer
            )
        )

        cls._remove_radius_rejection(
            username
        )

        return username

    @classmethod
    @transaction.atomic
    def remove_pppoe_customer(
        cls,
        customer,
    ):
        """
        Completely remove the customer's
        RADIUS records.
        """
        customer = (
            CustomerProfile.objects
            .select_for_update()
            .get(
                pk=customer.pk
            )
        )

        username = (
            cls.build_radius_username(
                customer
            )
        )

        RadiusCheck.objects.filter(
            username=username
        ).delete()

        RadiusReply.objects.filter(
            username=username
        ).delete()

        return username


class RadiusAccountingService:
    """
    Read-only service for FreeRADIUS accounting data.

    All organization-level queries are tenant-scoped
    through Lintech customer identities rather than
    exposing the raw radacct table directly.

    MikroTik PPP accounting is configured to send
    interim updates every five minutes. Lintech allows
    three missed intervals before considering an
    apparently active session stale.
    """

    INTERIM_UPDATE_INTERVAL = timedelta(
        minutes=5
    )

    STALE_SESSION_AFTER = timedelta(
        minutes=15
    )

    @staticmethod
    def _get_customer(
        organization,
        customer_id,
    ):
        try:
            return (
                CustomerProfile.objects
                .select_related(
                    "organization",
                    "package",
                    "router_info__router",
                )
                .get(
                    organization=organization,
                    customer_id=customer_id,
                )
            )

        except CustomerProfile.DoesNotExist:
            raise RadiusProvisioningError(
                "Customer not found in "
                "this organization."
            )

    @staticmethod
    def _organization_customers(
        organization,
    ):
        return (
            CustomerProfile.objects
            .filter(
                organization=organization
            )
            .select_related(
                "organization",
                "package",
                "router_info__router",
            )
        )

    @classmethod
    def _organization_username_map(
        cls,
        organization,
    ):
        """
        Return a mapping of generated RADIUS usernames
        to Lintech customers.

        Example:
            {
                "lintech-demo-test001": customer,
            }
        """
        username_map = {}

        for customer in (
            cls._organization_customers(
                organization
            )
        ):
            username = (
                RadiusProvisioningService
                .build_radius_username(
                    customer
                )
            )

            username_map[
                username
            ] = customer

        return username_map

    @classmethod
    def _session_cutoff(
        cls,
        now=None,
    ):
        """
        Return the oldest accounting timestamp that
        Lintech may still consider online.

        The MikroTik sends an interim update every
        five minutes. Three missed intervals are
        allowed before a session becomes stale.
        """
        current_time = (
            now
            or timezone.now()
        )

        return (
            current_time
            - cls.STALE_SESSION_AFTER
        )

    @classmethod
    def is_session_online(
        cls,
        session,
        now=None,
    ):
        """
        Determine whether one accounting row represents
        a genuinely online PPP session.

        Requirements:
        - accounting start exists
        - accounting stop does not exist
        - most recent accounting activity is fresh

        Before the first interim update arrives,
        acctstarttime acts as the freshness timestamp.
        """
        if (
            session.acctstarttime
            is None
        ):
            return False

        if (
            session.acctstoptime
            is not None
        ):
            return False

        last_seen = (
            session.acctupdatetime
            or session.acctstarttime
        )

        if last_seen is None:
            return False

        return (
            last_seen
            >= cls._session_cutoff(
                now
            )
        )

    @classmethod
    def all_sessions(
        cls,
        organization,
    ):
        """
        Return all RADIUS accounting sessions belonging
        to the organization's Lintech customers.
        """
        username_map = (
            cls._organization_username_map(
                organization
            )
        )

        if not username_map:
            return (
                RadAcct.objects.none()
            )

        return (
            RadAcct.objects
            .filter(
                username__in=(
                    username_map.keys()
                )
            )
            .order_by(
                "-acctstarttime",
                "-radacctid",
            )
        )

    @classmethod
    def active_sessions(
        cls,
        organization,
    ):
        """
        Return genuinely active RADIUS sessions.

        A missing accounting stop packet by itself
        is not sufficient proof that the customer
        remains connected.

        Sessions with no accounting activity within
        the stale threshold are excluded.
        """
        cutoff = (
            cls._session_cutoff()
        )

        return (
            cls.all_sessions(
                organization
            )
            .filter(
                acctstarttime__isnull=False,
                acctstoptime__isnull=True,
            )
            .filter(
                Q(
                    acctupdatetime__gte=cutoff
                )
                |
                Q(
                    acctupdatetime__isnull=True,
                    acctstarttime__gte=cutoff,
                )
            )
        )

    @classmethod
    def customer_sessions(
        cls,
        organization,
        customer_id,
    ):
        """
        Return accounting history for one customer.
        """
        customer = (
            cls._get_customer(
                organization,
                customer_id,
            )
        )

        username = (
            RadiusProvisioningService
            .build_radius_username(
                customer
            )
        )

        return (
            RadAcct.objects
            .filter(
                username=username
            )
            .order_by(
                "-acctstarttime",
                "-radacctid",
            )
        )

    @classmethod
    def latest_customer_session(
        cls,
        organization,
        customer_id,
    ):
        """
        Return the customer's newest accounting session,
        or None when no accounting history exists.
        """
        return (
            cls.customer_sessions(
                organization,
                customer_id,
            )
            .first()
        )

    @classmethod
    def customer_is_online(
        cls,
        organization,
        customer_id,
    ):
        """
        Determine online status using fresh accounting
        activity rather than only a missing stop packet.
        """
        cutoff = (
            cls._session_cutoff()
        )

        return (
            cls.customer_sessions(
                organization,
                customer_id,
            )
            .filter(
                acctstarttime__isnull=False,
                acctstoptime__isnull=True,
            )
            .filter(
                Q(
                    acctupdatetime__gte=cutoff
                )
                |
                Q(
                    acctupdatetime__isnull=True,
                    acctstarttime__gte=cutoff,
                )
            )
            .exists()
        )

    @classmethod
    def customer_totals(
        cls,
        organization,
        customer_id,
    ):
        """
        Return historical accounting totals for
        a single customer.
        """
        sessions = (
            cls.customer_sessions(
                organization,
                customer_id,
            )
        )

        totals = (
            sessions.aggregate(
                session_count=Count(
                    "radacctid"
                ),
                total_session_seconds=Sum(
                    "acctsessiontime"
                ),
                total_input_bytes=Sum(
                    "acctinputoctets"
                ),
                total_output_bytes=Sum(
                    "acctoutputoctets"
                ),
            )
        )

        return {
            "session_count": (
                totals[
                    "session_count"
                ]
                or 0
            ),
            "total_session_seconds": (
                totals[
                    "total_session_seconds"
                ]
                or 0
            ),
            "total_input_bytes": (
                totals[
                    "total_input_bytes"
                ]
                or 0
            ),
            "total_output_bytes": (
                totals[
                    "total_output_bytes"
                ]
                or 0
            ),
        }

    @classmethod
    def session_to_dict(
        cls,
        session,
        customer=None,
    ):
        """
        Convert one RadAcct row into the stable Lintech
        representation used by APIs.

        Byte direction is from the customer's point
        of view:

        acctinputoctets:
            bytes received by NAS from customer
            -> customer upload

        acctoutputoctets:
            bytes sent by NAS to customer
            -> customer download
        """
        router_info = None
        router = None

        if customer is not None:
            router_info = getattr(
                customer,
                "router_info",
                None,
            )

            if router_info:
                router = (
                    router_info.router
                )

        return {
            "id": (
                session.radacctid
            ),
            "username": (
                session.username
            ),
            "customer_id": (
                customer.customer_id
                if customer
                else None
            ),
            "customer_name": (
                customer.customer_name
                if customer
                else None
            ),
            "router_id": (
                router.id
                if router
                else None
            ),
            "router_name": (
                router.name
                if router
                else None
            ),
            "nas_ip_address": (
                session.nasipaddress
            ),
            "ip_address": (
                session.framedipaddress
            ),
            "mac_address": (
                session.callingstationid
            ),
            "started_at": (
                session.acctstarttime
            ),
            "updated_at": (
                session.acctupdatetime
            ),
            "stopped_at": (
                session.acctstoptime
            ),
            "duration_seconds": (
                session.acctsessiontime
                or 0
            ),
            "download_bytes": (
                session.acctoutputoctets
                or 0
            ),
            "upload_bytes": (
                session.acctinputoctets
                or 0
            ),
            "total_bytes": (
                session.total_bytes
            ),
            "online": (
                cls.is_session_online(
                    session
                )
            ),
            "terminate_cause": (
                session.acctterminatecause
            ),
            "service_type": (
                session.servicetype
            ),
        }

    @classmethod
    def organization_session_data(
        cls,
        organization,
        active_only=False,
    ):
        """
        Return organization accounting sessions enriched
        with Lintech customer and router information.
        """
        username_map = (
            cls._organization_username_map(
                organization
            )
        )

        if active_only:
            sessions = (
                cls.active_sessions(
                    organization
                )
            )

        else:
            sessions = (
                cls.all_sessions(
                    organization
                )
            )

        return [
            cls.session_to_dict(
                session,
                username_map.get(
                    session.username
                ),
            )
            for session in sessions
        ]

    @classmethod
    def customer_session_data(
        cls,
        organization,
        customer_id,
    ):
        """
        Return enriched accounting history for one
        Lintech customer.
        """
        customer = (
            cls._get_customer(
                organization,
                customer_id,
            )
        )

        sessions = (
            cls.customer_sessions(
                organization,
                customer_id,
            )
        )

        return [
            cls.session_to_dict(
                session,
                customer,
            )
            for session in sessions
        ]