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

        NOTE:
        CustomerProfile.customer_id is still globally unique in the database.
        We will change that later to organization + customer_id uniqueness.
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
                {"zone_id": ["Zone not found in this organization."]}
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
                {"package_id": ["Package not found in this organization."]}
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
                {"router_id": ["Router not found in this organization."]}
            )

    @staticmethod
    def check_pppoe_user_exists(organization, router_id, pppoe_name):
        """
        Check whether a PPPoE secret exists on one of the organization's routers.
        """
        if not router_id or not pppoe_name:
            return None

        from mikrotik.service.helpers import check_pppoe_user_exists_on_router

        router = CustomerService.get_router(
            organization=organization,
            router_id=router_id,
        )

        return check_pppoe_user_exists_on_router(router, pppoe_name)

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

        billing_day = min(int(billing_day), last_day)

        return next_month.replace(
            day=billing_day,
        ).date()

    @staticmethod
    @transaction.atomic
    def create_customer(organization, validated_data):
        """
        Create a new customer and optionally provision PPPoE on MikroTik.
        """
        router_id = validated_data.get("router_id")
        pppoe_name = validated_data.get("pppoe_name")

        if pppoe_name:
            pppoe_name = pppoe_name.lower()
            validated_data["pppoe_name"] = pppoe_name

        router = CustomerService.get_router(
            organization,
            router_id,
        )

        if router and pppoe_name:
            if RouterInfo.objects.filter(
                router=router,
                pppoe_name__iexact=pppoe_name,
            ).exists():
                raise serializers.ValidationError(
                    {
                        "pppoe_name": [
                            "PPPoE user already exists in the local database "
                            "for this router."
                        ]
                    }
                )

            try:
                existing_info = CustomerService.check_pppoe_user_exists(
                    organization,
                    router_id,
                    pppoe_name,
                )
            except serializers.ValidationError:
                raise
            except Exception as exc:
                raise serializers.ValidationError(
                    {
                        "pppoe_name": [
                            f"Error checking PPPoE user on router: {exc}"
                        ]
                    }
                )

            if existing_info:
                raise serializers.ValidationError(
                    {
                        "pppoe_name": [
                            "PPPoE user already exists on this MikroTik router."
                        ]
                    }
                )

        customer_id = (
            validated_data.get("customer_id")
            or CustomerService.generate_customer_id(organization)
        )

        zone = CustomerService.get_zone(
            organization,
            validated_data["zone_id"],
        )

        package = CustomerService.get_package(
            organization,
            validated_data.get("package_id"),
        )

        billing_date = CustomerService._calculate_next_billing_date(
            validated_data.get("billing_day", 1)
        )

        customer = CustomerProfile.objects.create(
            organization=organization,
            customer_id=customer_id,
            customer_name=validated_data["customer_name"],
            nid=validated_data.get("nid"),
            phone_number=validated_data["phone_number"],
            phone_number2=validated_data.get("phone_number2"),
            address=validated_data["address"],
            zone=zone,
            package=package,
            billing_date=billing_date,
        )

        if router:
            profile = validated_data.get("profile_name")

            if not profile and package:
                profile = package.name

            if not profile:
                profile = "default"

            pppoe_name = validated_data.get("pppoe_name")
            pppoe_pass = validated_data.get("pppoe_pass")

            if not pppoe_name:
                raise serializers.ValidationError(
                    {
                        "pppoe_name": [
                            "PPPoE name is required when a router is selected."
                        ]
                    }
                )

            if not pppoe_pass:
                raise serializers.ValidationError(
                    {
                        "pppoe_pass": [
                            "PPPoE password is required when a router is selected."
                        ]
                    }
                )

            RouterInfo.objects.create(
                pppoe_name=pppoe_name,
                pppoe_pass=pppoe_pass,
                profile_name=profile,
                remote_ip=validated_data.get("remote_ip"),
                customer=customer,
                router=router,
            )

            try:
                from mikrotik.service.helpers import (
                    create_pppoe_user_on_router,
                    generate_customer_comment,
                )

                service = (
                    validated_data.get("service_type")
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
    def link_existing_customer(organization, validated_data):
        """
        Link a new customer record to an existing MikroTik PPPoE secret.
        """
        router_id = validated_data.get("router_id")
        pppoe_name = validated_data.get("pppoe_name")

        router = CustomerService.get_router(
            organization,
            router_id,
        )

        if not router:
            raise serializers.ValidationError(
                {"router_id": ["Router is required."]}
            )

        if not pppoe_name:
            raise serializers.ValidationError(
                {"pppoe_name": ["PPPoE name is required."]}
            )

        pppoe_name = pppoe_name.lower()
        validated_data["pppoe_name"] = pppoe_name

        if RouterInfo.objects.filter(
            router=router,
            pppoe_name__iexact=pppoe_name,
        ).exists():
            raise serializers.ValidationError(
                {
                    "pppoe_name": [
                        "PPPoE user is already linked to a customer "
                        "in the local database."
                    ]
                }
            )

        try:
            existing_info = CustomerService.check_pppoe_user_exists(
                organization,
                router_id,
                pppoe_name,
            )
        except serializers.ValidationError:
            raise
        except Exception as exc:
            raise serializers.ValidationError(
                {
                    "pppoe_name": [
                        f"Error checking PPPoE user on router: {exc}"
                    ]
                }
            )

        if not existing_info:
            raise serializers.ValidationError(
                {
                    "pppoe_name": [
                        "PPPoE user does not exist on this router. Cannot link."
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
            or existing_info.get("remote-address")
        )

        customer_id = (
            validated_data.get("customer_id")
            or CustomerService.generate_customer_id(organization)
        )

        zone = CustomerService.get_zone(
            organization,
            validated_data["zone_id"],
        )

        package = CustomerService.get_package(
            organization,
            validated_data.get("package_id"),
        )

        billing_date = CustomerService._calculate_next_billing_date(
            validated_data.get("billing_day", 1)
        )

        customer = CustomerProfile.objects.create(
            organization=organization,
            customer_id=customer_id,
            customer_name=validated_data["customer_name"],
            nid=validated_data.get("nid"),
            phone_number=validated_data["phone_number"],
            phone_number2=validated_data.get("phone_number2"),
            address=validated_data["address"],
            zone=zone,
            package=package,
            billing_date=billing_date,
        )

        RouterInfo.objects.create(
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
                        f"MikroTik Error during linking: {exc}"
                    ]
                }
            )

        return customer

    @staticmethod
    def get_all_customers(organization):
        """
        Return customers belonging only to the supplied organization.
        """
        return (
            CustomerProfile.objects
            .filter(organization=organization)
            .select_related(
                "zone",
                "package",
                "router_info",
            )
        )

    @staticmethod
    def get_online_pppoe_names(organization):
        """
        Return PPPoE names currently active across the organization's routers.
        """
        from mikrotik.service.connection import MikrotikConnection
        from mikrotik.service.tools import get_active_customers

        names = set()

        routers = MikrotikRouter.objects.filter(
            organization=organization,
            is_active=True,
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

                result = get_active_customers(conn.api)

                if result.get("status") == "Success":
                    for item in result.get("customers", []):
                        name = item.get("name")

                        if name:
                            names.add(name.lower())

            except Exception:
                continue

        return names

    @staticmethod
    def get_customer_details(organization, customer_id):
        """
        Return one customer only if the customer belongs to the organization.
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
            base = customer.billing_date or timezone.now().date()

            last_day = calendar.monthrange(
                base.year,
                base.month,
            )[1]

            day = min(
                int(billing_day),
                last_day,
                28,
            )

            customer.billing_date = base.replace(day=day)

        if extended_billing_days is not None:
            customer.extended_billing_days = max(
                0,
                int(extended_billing_days),
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
        Update customer status locally and best-effort sync to MikroTik.
        """
        from mikrotik.service.helpers import (
            update_pppoe_status_on_router,
        )

        customer = (
            CustomerProfile.objects
            .filter(
                organization=organization,
                customer_id=customer_id,
            )
            .select_related("router_info__router")
            .first()
        )

        if not customer:
            raise serializers.ValidationError(
                {"customer": ["Customer not found."]}
            )

        if customer.customer_status == status_value:
            return customer, None

        customer.customer_status = status_value

        customer.save(
            update_fields=[
                "customer_status",
                "updated_at",
            ]
        )

        warning = None

        info = getattr(customer, "router_info", None)

        if info and info.router:
            disabled = status_value == "disconnected"

            try:
                update_pppoe_status_on_router(
                    info.router,
                    info.pppoe_name,
                    disabled,
                )
            except Exception as exc:
                warning = (
                    "Status saved locally, but router sync failed: "
                    f"{exc}"
                )

        return customer, warning

    @staticmethod
    def update_customer_connection(
        organization,
        customer_id,
        data,
    ):
        """
        Update PPPoE/router information without allowing cross-tenant routers.
        """
        from mikrotik.service.helpers import (
            update_pppoe_secret_on_router,
        )

        customer = (
            CustomerProfile.objects
            .filter(
                organization=organization,
                customer_id=customer_id,
            )
            .select_related("router_info__router")
            .first()
        )

        if not customer:
            raise serializers.ValidationError(
                {"customer": ["Customer not found."]}
            )

        info = getattr(customer, "router_info", None)

        if not info:
            raise serializers.ValidationError(
                {
                    "router_info": [
                        "This customer has no PPPoE connection to edit."
                    ]
                }
            )

        for field in (
            "pppoe_name",
            "pppoe_pass",
            "profile_name",
            "remote_ip",
        ):
            if field in data and data[field] is not None:
                setattr(info, field, data[field])

        if "router" in data:
            router_id = data.get("router")

            if router_id:
                router = CustomerService.get_router(
                    organization,
                    router_id,
                )
                info.router = router
            else:
                info.router = None

        info.save()

        warning = None

        if info.router:
            try:
                update_pppoe_secret_on_router(
                    info.router,
                    info.pppoe_name,
                    profile=info.profile_name or None,
                    password=info.pppoe_pass or None,
                )
            except Exception as exc:
                warning = (
                    "Saved locally, but router sync failed: "
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
        Delete a customer and remove their PPPoE account from MikroTik.
        """
        from mikrotik.service.helpers import (
            delete_pppoe_user_from_router,
        )

        customer = (
            CustomerProfile.objects
            .filter(
                organization=organization,
                customer_id=customer_id,
            )
            .select_related("router_info__router")
            .first()
        )

        if not customer:
            raise serializers.ValidationError(
                {"customer": ["Customer not found."]}
            )

        info = getattr(customer, "router_info", None)

        if info and info.router:
            try:
                delete_pppoe_user_from_router(
                    info.router,
                    info.pppoe_name,
                )
            except Exception as exc:
                raise serializers.ValidationError(
                    {
                        "customer": [
                            "Failed to delete user from MikroTik router: "
                            f"{exc}. Deletion rolled back."
                        ]
                    }
                )

        customer.delete()