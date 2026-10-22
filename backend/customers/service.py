import calendar

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from billing.models import Package
from mikrotik.models import MikrotikRouter, RouterInfo

from .models import AddressZone, CustomerProfile


class CustomerService:
    @staticmethod
    def generate_customer_id(organization):
        """
        Generate the next customer ID within an organization.
        """
        last_customer = (
            CustomerProfile.objects
            .filter(organization=organization)
            .order_by("-id")
            .first()
        )

        if last_customer:
            try:
                number = int(last_customer.customer_id)
                return f"{number + 1:06d}"
            except (TypeError, ValueError):
                pass

        return "000001"

    @staticmethod
    def get_zone(organization, zone_id):
        try:
            return AddressZone.objects.get(
                id=zone_id,
                organization=organization,
            )
        except AddressZone.DoesNotExist:
            raise serializers.ValidationError(
                {
                    "zone_id": [
                        "Zone not found in this organization."
                    ]
                }
            )

    @staticmethod
    def get_package(organization, package_id):
        if not package_id:
            return None

        try:
            return Package.objects.get(
                id=package_id,
                organization=organization,
            )
        except Package.DoesNotExist:
            raise serializers.ValidationError(
                {
                    "package_id": [
                        "Package not found in this organization."
                    ]
                }
            )

    @staticmethod
    def get_router(organization, router_id):
        if not router_id:
            return None

        try:
            return MikrotikRouter.objects.get(
                id=router_id,
                organization=organization,
            )
        except MikrotikRouter.DoesNotExist:
            raise serializers.ValidationError(
                {
                    "router_id": [
                        "Router not found in this organization."
                    ]
                }
            )

    @staticmethod
    def check_pppoe_user_exists(
        organization,
        router_id,
        pppoe_name,
    ):
        """
        Check whether a PPPoE secret exists on one of the
        organization's routers.
        """
        if not router_id or not pppoe_name:
            return None

        from mikrotik.service.helpers import (
            check_pppoe_user_exists_on_router,
        )

        router = CustomerService.get_router(
            organization=organization,
            router_id=router_id,
        )

        return check_pppoe_user_exists_on_router(
            router,
            pppoe_name,
        )

    @staticmethod
    def _calculate_next_billing_date(billing_day):
        today = timezone.now()

        if today.month == 12:
            next_month = today.replace(
                year=today.year + 1,
                month=1,
                day=1,
            )
        else:
            next_month = today.replace(
                month=today.month + 1,
                day=1,
            )

        last_day = calendar.monthrange(
            next_month.year,
            next_month.month,
        )[1]

        billing_day = min(
            int(billing_day),
            last_day,
        )

        return next_month.replace(
            day=billing_day,
        ).date()

    @staticmethod
    @transaction.atomic
    def create_customer(
        organization,
        validated_data,
    ):
        """
        Create a customer and provision PPPoE according to
        authentication mode.

        local_secret:
            Creates a local /ppp secret on MikroTik.

        radius:
            Creates FreeRADIUS authorization records and does
            not create a local MikroTik secret.
        """
        authentication_mode = validated_data.get(
            "authentication_mode",
            "local_secret",
        )

        router_id = validated_data.get("router_id")

        router = CustomerService.get_router(
            organization,
            router_id,
        )

        package = CustomerService.get_package(
            organization,
            validated_data.get("package_id"),
        )

        if authentication_mode == "radius":
            password = validated_data.get("pppoe_pass")
            if not isinstance(password, str) or not password.strip():
                raise serializers.ValidationError({
                    "pppoe_pass": ["A non-empty PPPoE password is required for a RADIUS customer."],
                })
            if "pppoe_name" in validated_data:
                raise serializers.ValidationError({
                    "pppoe_name": ["RADIUS usernames are generated by Lintech; omit this field."],
                })
            if not router:
                raise serializers.ValidationError(
                    {
                        "router_id": [
                            "Router is required for a "
                            "RADIUS-managed customer."
                        ]
                    }
                )

            if not package:
                raise serializers.ValidationError(
                    {
                        "package_id": [
                            "Package is required for a "
                            "RADIUS-managed customer."
                        ]
                    }
                )

            if not package.is_active:
                raise serializers.ValidationError(
                    {
                        "package_id": [
                            "The selected package is inactive."
                        ]
                    }
                )

        pppoe_name = validated_data.get("pppoe_name")

        if pppoe_name:
            pppoe_name = pppoe_name.lower()
            validated_data["pppoe_name"] = pppoe_name

        # -------------------------------------------------
        # Local-secret duplicate checks
        # -------------------------------------------------
        if (
            authentication_mode == "local_secret"
            and router
            and pppoe_name
        ):
            if RouterInfo.objects.filter(
                router=router,
                pppoe_name__iexact=pppoe_name,
            ).exists():
                raise serializers.ValidationError(
                    {
                        "pppoe_name": [
                            "PPPoE user already exists in the "
                            "local database for this router."
                        ]
                    }
                )

            try:
                existing_info = (
                    CustomerService.check_pppoe_user_exists(
                        organization,
                        router_id,
                        pppoe_name,
                    )
                )

            except serializers.ValidationError:
                raise

            except Exception as exc:
                raise serializers.ValidationError(
                    {
                        "pppoe_name": [
                            "Error checking PPPoE user on "
                            f"router: {exc}"
                        ]
                    }
                )

            if existing_info:
                raise serializers.ValidationError(
                    {
                        "pppoe_name": [
                            "PPPoE user already exists on this "
                            "MikroTik router."
                        ]
                    }
                )

        customer_id = (
            validated_data.get("customer_id")
            or CustomerService.generate_customer_id(
                organization
            )
        )

        zone = CustomerService.get_zone(
            organization,
            validated_data["zone_id"],
        )

        billing_date = (
            CustomerService._calculate_next_billing_date(
                validated_data.get(
                    "billing_day",
                    1,
                )
            )
        )

        customer = CustomerProfile.objects.create(
            organization=organization,
            customer_id=customer_id,
            customer_name=validated_data[
                "customer_name"
            ],
            nid=validated_data.get("nid"),
            phone_number=validated_data[
                "phone_number"
            ],
            phone_number2=validated_data.get(
                "phone_number2"
            ),
            address=validated_data["address"],
            zone=zone,
            package=package,
            billing_date=billing_date,
        )

        # -------------------------------------------------
        # No router selected
        # -------------------------------------------------
        if not router:
            return customer

        # -------------------------------------------------
        # RADIUS-managed PPPoE customer
        # -------------------------------------------------
        if authentication_mode == "radius":
            from radius.services import (
                RadiusProvisioningService,
            )

            try:
                radius_result = (
                    RadiusProvisioningService
                    .provision_pppoe_customer(
                        customer,
                        password=password,
                        reset_password=True,
                    )
                )

            except Exception:
                # Database/driver errors may include bound credential values.
                raise serializers.ValidationError({
                    "router_info": ["RADIUS provisioning failed. Please contact support."],
                }) from None

            RouterInfo.objects.create(
                authentication_mode="radius",
                pppoe_name=radius_result[
                    "username"
                ],
                pppoe_pass=radius_result[
                    "password"
                ],
                profile_name=(
                    validated_data.get(
                        "profile_name"
                    )
                    or package.name
                ),
                remote_ip=validated_data.get(
                    "remote_ip"
                ),
                customer=customer,
                router=router,
            )

            return customer

        # -------------------------------------------------
        # Existing local-secret PPPoE workflow
        # -------------------------------------------------
        profile = validated_data.get(
            "profile_name"
        )

        if not profile and package:
            profile = package.name

        if not profile:
            profile = "default"

        pppoe_name = validated_data.get(
            "pppoe_name"
        )

        pppoe_pass = validated_data.get(
            "pppoe_pass"
        )

        if not pppoe_name:
            raise serializers.ValidationError(
                {
                    "pppoe_name": [
                        "PPPoE name is required when a "
                        "router is selected."
                    ]
                }
            )

        if not pppoe_pass:
            raise serializers.ValidationError(
                {
                    "pppoe_pass": [
                        "PPPoE password is required when "
                        "a router is selected."
                    ]
                }
            )

        RouterInfo.objects.create(
            authentication_mode="local_secret",
            pppoe_name=pppoe_name,
            pppoe_pass=pppoe_pass,
            profile_name=profile,
            remote_ip=validated_data.get(
                "remote_ip"
            ),
            customer=customer,
            router=router,
        )

        try:
            from mikrotik.service.helpers import (
                create_pppoe_user_on_router,
                generate_customer_comment,
            )

            service = (
                validated_data.get(
                    "service_type"
                )
                or "pppoe"
            ).lower()

            comment = generate_customer_comment(
                customer_id=customer.customer_id,
                customer_name=customer.customer_name,
                phone_number=customer.phone_number,
                address=customer.address,
                zone_name=zone.name,
            )

            create_pppoe_user_on_router(
                router=router,
                pppoe_name=pppoe_name,
                pppoe_pass=pppoe_pass,
                profile=profile,
                service=service,
                comment=comment,
            )

        except Exception as exc:
            raise serializers.ValidationError(
                {
                    "router_info": [
                        f"MikroTik Error: {exc}"
                    ]
                }
            )

        return customer

    @staticmethod
    @transaction.atomic
    def link_existing_customer(
        organization,
        validated_data,
    ):
        """
        Link a customer to an existing local MikroTik
        PPPoE secret.
        """
        router_id = validated_data.get(
            "router_id"
        )

        pppoe_name = validated_data.get(
            "pppoe_name"
        )

        router = CustomerService.get_router(
            organization,
            router_id,
        )

        if not router:
            raise serializers.ValidationError(
                {
                    "router_id": [
                        "Router is required."
                    ]
                }
            )

        if not pppoe_name:
            raise serializers.ValidationError(
                {
                    "pppoe_name": [
                        "PPPoE name is required."
                    ]
                }
            )

        pppoe_name = pppoe_name.lower()
        validated_data["pppoe_name"] = (
            pppoe_name
        )

        if RouterInfo.objects.filter(
            router=router,
            pppoe_name__iexact=pppoe_name,
        ).exists():
            raise serializers.ValidationError(
                {
                    "pppoe_name": [
                        "PPPoE user is already linked to "
                        "a customer in the local database."
                    ]
                }
            )

        try:
            existing_info = (
                CustomerService
                .check_pppoe_user_exists(
                    organization,
                    router_id,
                    pppoe_name,
                )
            )

        except serializers.ValidationError:
            raise

        except Exception as exc:
            raise serializers.ValidationError(
                {
                    "pppoe_name": [
                        "Error checking PPPoE user on "
                        f"router: {exc}"
                    ]
                }
            )

        if not existing_info:
            raise serializers.ValidationError(
                {
                    "pppoe_name": [
                        "PPPoE user does not exist on "
                        "this router. Cannot link."
                    ]
                }
            )

        pppoe_pass = (
            validated_data.get("pppoe_pass")
            or existing_info.get("password")
            or ""
        )

        profile_name = (
            validated_data.get("profile_name")
            or existing_info.get("profile")
            or "default"
        )

        remote_ip = (
            validated_data.get("remote_ip")
            or existing_info.get(
                "remote-address"
            )
        )

        customer_id = (
            validated_data.get("customer_id")
            or CustomerService
            .generate_customer_id(
                organization
            )
        )

        zone = CustomerService.get_zone(
            organization,
            validated_data["zone_id"],
        )

        package = CustomerService.get_package(
            organization,
            validated_data.get(
                "package_id"
            ),
        )

        billing_date = (
            CustomerService
            ._calculate_next_billing_date(
                validated_data.get(
                    "billing_day",
                    1,
                )
            )
        )

        customer = CustomerProfile.objects.create(
            organization=organization,
            customer_id=customer_id,
            customer_name=validated_data[
                "customer_name"
            ],
            nid=validated_data.get("nid"),
            phone_number=validated_data[
                "phone_number"
            ],
            phone_number2=validated_data.get(
                "phone_number2"
            ),
            address=validated_data[
                "address"
            ],
            zone=zone,
            package=package,
            billing_date=billing_date,
        )

        RouterInfo.objects.create(
            authentication_mode="local_secret",
            pppoe_name=pppoe_name,
            pppoe_pass=pppoe_pass,
            profile_name=profile_name,
            remote_ip=remote_ip,
            customer=customer,
            router=router,
        )

        try:
            from mikrotik.service.helpers import (
                generate_customer_comment,
                update_pppoe_comment_on_router,
            )

            comment = generate_customer_comment(
                customer_id=customer.customer_id,
                customer_name=customer.customer_name,
                phone_number=customer.phone_number,
                address=customer.address,
                zone_name=zone.name,
            )

            update_pppoe_comment_on_router(
                router=router,
                pppoe_name=pppoe_name,
                comment=comment,
            )

        except Exception as exc:
            raise serializers.ValidationError(
                {
                    "router_info": [
                        "MikroTik Error during linking: "
                        f"{exc}"
                    ]
                }
            )

        return customer

    @staticmethod
    @transaction.atomic
    def update_customer_profile(organization, customer_id, validated_data):
        """Save profile and changed RADIUS package in one database transaction.

        Reply changes take effect on subsequent authentication. This operation
        does not disconnect active sessions, reset credentials, or migrate
        local MikroTik profiles.
        """
        from radius.models import RadiusCheck
        from radius.services import RadiusProvisioningService

        customer = (
            CustomerProfile.objects.select_for_update()
            .get(organization=organization, customer_id=customer_id)
        )
        info = (
            RouterInfo.objects.select_for_update()
            .filter(customer=customer).first()
        )
        is_radius = info is not None and info.authentication_mode == "radius"
        package_changed = False
        if "package" in validated_data:
            requested_package = validated_data["package"]
            if is_radius and requested_package is None:
                raise serializers.ValidationError({
                    "package": ["A RADIUS customer must have a package."],
                })
            package_id = requested_package.pk if requested_package else None
            package_changed = package_id != customer.package_id
            if requested_package is not None:
                # Re-read under lock; serializer validation happened before
                # this transaction and package settings could have changed.
                requested_package = (
                    Package.objects.select_for_update()
                    .filter(pk=package_id, organization=organization).first()
                )
                if requested_package is None:
                    raise serializers.ValidationError({
                        "package": ["Package not found in this organization."],
                    })
                if is_radius and package_changed and not requested_package.is_active:
                    raise serializers.ValidationError({
                        "package": ["The selected package is inactive."],
                    })
            validated_data = {**validated_data, "package": requested_package}

        if is_radius and package_changed:
            try:
                radius_username = RadiusProvisioningService.build_radius_username(customer)
                if info.pppoe_name != radius_username:
                    raise serializers.ValidationError({
                        "package": ["RADIUS connection identity requires repair before changing package."],
                    })
                password_record = (
                    RadiusCheck.objects.select_for_update()
                    .filter(username=radius_username, attribute="Cleartext-Password")
                    .order_by("id").first()
                )
                if password_record is None or not password_record.value:
                    raise serializers.ValidationError({
                        "package": ["RADIUS credentials require repair before changing package."],
                    })
            except serializers.ValidationError:
                raise
            except Exception:
                raise serializers.ValidationError({
                    "package": ["RADIUS credentials could not be verified. No profile changes were saved."],
                }) from None

        for field, value in validated_data.items():
            setattr(customer, field, value)
        customer.save()

        if is_radius and package_changed:
            try:
                RadiusProvisioningService.provision_pppoe_customer(
                    customer, password=None, reset_password=False,
                )
            except Exception:
                # Driver errors may contain bound credential values. Roll back
                # both the profile and unmanaged RADIUS tables without echoing.
                raise serializers.ValidationError({
                    "package": ["RADIUS package synchronization failed. No profile changes were saved."],
                }) from None

        return customer

    @staticmethod
    def get_all_customers(organization):
        """
        Return customers belonging to the supplied
        organization.
        """
        return (
            CustomerProfile.objects
            .filter(
                organization=organization
            )
            .select_related(
                "zone",
                "package",
                "router_info",
            )
        )

    @staticmethod
    def get_online_pppoe_names(
        organization,
    ):
        """
        Return PPPoE usernames currently active across
        the organization's routers.
        """
        from mikrotik.service.connection import (
            MikrotikConnection,
        )
        from mikrotik.service.tools import (
            get_active_customers,
        )

        names = set()

        routers = (
            MikrotikRouter.objects
            .filter(
                organization=organization,
                is_active=True,
            )
        )

        for router in routers:
            try:
                conn = MikrotikConnection(
                    host=router.host,
                    port=router.port,
                    username=router.username,
                    password=router.password,
                )

                if not conn.api:
                    continue

                result = get_active_customers(
                    conn.api
                )

                if (
                    result.get("status")
                    == "Success"
                ):
                    for item in result.get(
                        "customers",
                        [],
                    ):
                        name = item.get("name")

                        if name:
                            names.add(
                                name.lower()
                            )

            except Exception:
                continue

        return names

    @staticmethod
    def get_customer_details(
        organization,
        customer_id,
    ):
        """
        Return one customer only when the customer belongs
        to the organization.
        """
        return (
            CustomerProfile.objects
            .filter(
                organization=organization,
                customer_id=customer_id,
            )
            .select_related(
                "zone",
                "package",
                "router_info__router",
            )
            .first()
        )

    @staticmethod
    def update_billing_settings(
        organization,
        customer_id,
        billing_day=None,
        extended_billing_days=None,
    ):
        customer = (
            CustomerProfile.objects
            .filter(
                organization=organization,
                customer_id=customer_id,
            )
            .first()
        )

        if not customer:
            return None

        if billing_day is not None:
            base = (
                customer.billing_date
                or timezone.now().date()
            )

            last_day = calendar.monthrange(
                base.year,
                base.month,
            )[1]

            day = min(
                int(billing_day),
                last_day,
                28,
            )

            customer.billing_date = (
                base.replace(day=day)
            )

        if extended_billing_days is not None:
            customer.extended_billing_days = max(
                0,
                int(
                    extended_billing_days
                ),
            )

        customer.save()

        return customer

    @staticmethod
    def update_customer_status(
        organization,
        customer_id,
        status_value,
    ):
        """
        Update customer status and synchronize the PPPoE
        authentication mechanism.

        local_secret:
            Enable or disable the MikroTik /ppp secret.

        radius:
            Update FreeRADIUS authorization and disconnect
            an existing PPPoE session when suspended.
        """
        from mikrotik.service.helpers import (
            disconnect_pppoe_session_on_router,
            update_pppoe_status_on_router,
        )
        from radius.services import (
            RadiusProvisioningService,
        )

        customer = (
            CustomerProfile.objects
            .filter(
                organization=organization,
                customer_id=customer_id,
            )
            .select_related(
                "router_info__router",
            )
            .first()
        )

        if not customer:
            raise serializers.ValidationError(
                {
                    "customer": [
                        "Customer not found."
                    ]
                }
            )

        if (
            customer.customer_status
            == status_value
        ):
            return customer, None

        customer.customer_status = (
            status_value
        )

        customer.save(
            update_fields=[
                "customer_status",
                "updated_at",
            ]
        )

        warning = None

        info = getattr(
            customer,
            "router_info",
            None,
        )

        if not info:
            return customer, None

        authentication_mode = getattr(
            info,
            "authentication_mode",
            "local_secret",
        )

        # -------------------------------------------------
        # RADIUS-managed PPPoE
        # -------------------------------------------------
        if authentication_mode == "radius":
            try:
                radius_username = (
                    RadiusProvisioningService
                    .build_radius_username(
                        customer
                    )
                )

                if status_value == "active":
                    (
                        RadiusProvisioningService
                        .provision_pppoe_customer(
                            customer
                        )
                    )

                else:
                    (
                        RadiusProvisioningService
                        .suspend_pppoe_customer(
                            customer
                        )
                    )

                    if info.router:
                        (
                            disconnect_pppoe_session_on_router(
                                info.router,
                                radius_username,
                            )
                        )

            except Exception as exc:
                warning = (
                    "Status saved locally, but "
                    "RADIUS/router sync failed: "
                    f"{exc}"
                )

            return customer, warning

        # -------------------------------------------------
        # Local MikroTik secret
        # -------------------------------------------------
        if info.router:
            disabled = (
                status_value
                == "disconnected"
            )

            try:
                update_pppoe_status_on_router(
                    info.router,
                    info.pppoe_name,
                    disabled,
                )

            except Exception as exc:
                warning = (
                    "Status saved locally, but "
                    "router sync failed: "
                    f"{exc}"
                )

        return customer, warning

    @staticmethod
    @transaction.atomic
    def update_customer_connection(
        organization,
        customer_id,
        data,
    ):
        """
        Update PPPoE/router information.

        RADIUS customers:
            FreeRADIUS is the credential source of truth.
            Any requested password change is written to
            radcheck first, and RouterInfo is then synchronized
            from the provisioning result in the same database
            transaction. The generated RADIUS username cannot
            be changed manually.

        Local-secret customers:
            Connection settings are stored locally and then
            synchronized directly with MikroTik.
        """
        from mikrotik.service.helpers import (
            update_pppoe_secret_on_router,
        )
        from radius.services import (
            RadiusProvisioningService,
        )

        customer = (
            CustomerProfile.objects
            .filter(
                organization=organization,
                customer_id=customer_id,
            )
            .select_related(
                "package",
                "router_info__router",
            )
            .first()
        )

        if not customer:
            raise serializers.ValidationError(
                {
                    "customer": [
                        "Customer not found."
                    ]
                }
            )

        info = getattr(
            customer,
            "router_info",
            None,
        )

        if not info:
            raise serializers.ValidationError(
                {
                    "router_info": [
                        "This customer has no PPPoE "
                        "connection to edit."
                    ]
                }
            )

        authentication_mode = getattr(
            info,
            "authentication_mode",
            "local_secret",
        )

        # -------------------------------------------------
        # RADIUS-managed PPPoE
        # -------------------------------------------------
        if authentication_mode == "radius":
            radius_username = (
                RadiusProvisioningService
                .build_radius_username(
                    customer
                )
            )

            requested_name = data.get(
                "pppoe_name"
            )

            if (
                requested_name is not None
                and requested_name.strip().lower()
                != radius_username.lower()
            ):
                raise serializers.ValidationError(
                    {
                        "pppoe_name": [
                            "RADIUS usernames are generated "
                            "by Lintech and cannot be changed "
                            "manually."
                        ]
                    }
                )

            if "router" in data:
                router_id = data.get(
                    "router"
                )

                if not router_id:
                    raise serializers.ValidationError(
                        {
                            "router": [
                                "A router is required for a "
                                "RADIUS-managed customer."
                            ]
                        }
                    )

                info.router = (
                    CustomerService.get_router(
                        organization,
                        router_id,
                    )
                )

            if (
                "profile_name" in data
                and data["profile_name"] is not None
            ):
                info.profile_name = (
                    data["profile_name"]
                )

            if (
                "remote_ip" in data
                and data["remote_ip"] is not None
            ):
                info.remote_ip = (
                    data["remote_ip"]
                )

            password_supplied = (
                "pppoe_pass" in data
            )

            requested_password = (
                data.get("pppoe_pass")
                if password_supplied
                else None
            )

            if (
                password_supplied
                and (
                    not isinstance(requested_password, str)
                    or not requested_password.strip()
                )
            ):
                raise serializers.ValidationError(
                    {
                        "pppoe_pass": [
                            "RADIUS password cannot be empty."
                        ]
                    }
                )

            try:
                radius_result = (
                    RadiusProvisioningService
                    .provision_pppoe_customer(
                        customer,
                        password=requested_password,
                        reset_password=password_supplied,
                    )
                )

            except serializers.ValidationError:
                raise

            except Exception:
                raise serializers.ValidationError({
                    "router_info": ["RADIUS connection update failed. Please contact support."],
                }) from None

            # FreeRADIUS is authoritative for generated
            # credentials. Synchronize RouterInfo only after
            # provisioning succeeds so the two stores cannot
            # drift apart.
            info.pppoe_name = (
                radius_result["username"]
            )
            info.pppoe_pass = (
                radius_result["password"]
            )

            if (
                not info.profile_name
                and customer.package
            ):
                info.profile_name = (
                    customer.package.name
                )

            info.save()

            return customer, None

        # -------------------------------------------------
        # Local MikroTik secret
        # -------------------------------------------------
        for field in (
            "pppoe_name",
            "pppoe_pass",
            "profile_name",
            "remote_ip",
        ):
            if (
                field in data
                and data[field] is not None
            ):
                setattr(
                    info,
                    field,
                    data[field],
                )

        if "router" in data:
            router_id = data.get(
                "router"
            )

            if router_id:
                info.router = (
                    CustomerService.get_router(
                        organization,
                        router_id,
                    )
                )
            else:
                info.router = None

        info.save()

        warning = None

        if info.router:
            try:
                update_pppoe_secret_on_router(
                    info.router,
                    info.pppoe_name,
                    profile=(
                        info.profile_name
                        or None
                    ),
                    password=(
                        info.pppoe_pass
                        or None
                    ),
                )

            except Exception as exc:
                warning = (
                    "Saved locally, but "
                    "router sync failed: "
                    f"{exc}"
                )

        return customer, warning

    @staticmethod
    @transaction.atomic
    def delete_customer_profile(
        organization,
        customer_id,
    ):
        """
        Delete a customer and remove PPPoE authorization.

        RADIUS:
            Remove radcheck/radreply records and disconnect
            an active PPP session.

        local_secret:
            Delete the MikroTik /ppp secret.
        """
        from mikrotik.service.helpers import (
            delete_pppoe_user_from_router,
            disconnect_pppoe_session_on_router,
        )
        from radius.services import (
            RadiusProvisioningService,
        )

        customer = (
            CustomerProfile.objects
            .filter(
                organization=organization,
                customer_id=customer_id,
            )
            .select_related(
                "router_info__router"
            )
            .first()
        )

        if not customer:
            raise serializers.ValidationError(
                {
                    "customer": [
                        "Customer not found."
                    ]
                }
            )

        info = getattr(
            customer,
            "router_info",
            None,
        )

        if info:
            if (
                info.authentication_mode
                == "radius"
            ):
                try:
                    radius_username = (
                        RadiusProvisioningService
                        .build_radius_username(
                            customer
                        )
                    )

                    (
                        RadiusProvisioningService
                        .remove_pppoe_customer(
                            customer
                        )
                    )

                    if info.router:
                        (
                            disconnect_pppoe_session_on_router(
                                info.router,
                                radius_username,
                            )
                        )

                except Exception as exc:
                    raise serializers.ValidationError(
                        {
                            "customer": [
                                "Failed to remove "
                                "RADIUS customer access: "
                                f"{exc}. Deletion "
                                "rolled back."
                            ]
                        }
                    )

            elif info.router:
                try:
                    (
                        delete_pppoe_user_from_router(
                            info.router,
                            info.pppoe_name,
                        )
                    )

                except Exception as exc:
                    raise serializers.ValidationError(
                        {
                            "customer": [
                                "Failed to delete user "
                                "from MikroTik router: "
                                f"{exc}. Deletion "
                                "rolled back."
                            ]
                        }
                    )

        customer.delete()