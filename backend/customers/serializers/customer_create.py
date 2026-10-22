from rest_framework import serializers

from customers.models import CustomerProfile
from mikrotik.models import RouterInfo


class CustomerRouterInfoSerializer(serializers.ModelSerializer):
    router_name = serializers.CharField(
        source="router.name",
        read_only=True,
    )

    class Meta:
        model = RouterInfo
        fields = [
            "id",
            "authentication_mode",
            "pppoe_name",
            "profile_name",
            "remote_ip",
            "router",
            "router_name",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class CustomerCreateSerializer(serializers.Serializer):
    customer_id = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    customer_name = serializers.CharField(
        max_length=255,
    )

    nid = serializers.CharField(
        max_length=15,
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    phone_number = serializers.CharField(
        max_length=15,
    )

    phone_number2 = serializers.CharField(
        max_length=15,
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    address = serializers.CharField(
        max_length=255,
    )

    zone_id = serializers.IntegerField()

    package_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )

    billing_day = serializers.IntegerField(
        min_value=1,
        max_value=28,
        required=False,
        default=1,
        write_only=True,
    )

    authentication_mode = serializers.ChoiceField(
        choices=RouterInfo.AUTHENTICATION_MODE_CHOICES,
        required=False,
        default="local_secret",
        write_only=True,
    )

    pppoe_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        write_only=True,
    )

    pppoe_pass = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        write_only=True,
    )

    remote_ip = serializers.IPAddressField(
        required=False,
        allow_null=True,
        write_only=True,
    )

    router_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True,
    )

    profile_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        write_only=True,
    )

    service_type = serializers.CharField(
        max_length=50,
        required=False,
        default="PPPoE",
        write_only=True,
    )

    # Response fields
    id = serializers.IntegerField(
        read_only=True,
    )

    billing_date = serializers.DateField(
        read_only=True,
    )

    customer_status = serializers.CharField(
        read_only=True,
    )

    balance = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    router_info = CustomerRouterInfoSerializer(
        read_only=True,
    )

    created_at = serializers.DateTimeField(
        read_only=True,
    )

    updated_at = serializers.DateTimeField(
        read_only=True,
    )

    def get_fields(self):
        fields = super().get_fields()
        if getattr(self, "initial_data", {}).get("authentication_mode") == "radius":
            # Preserve the operator's password exactly. Local-secret input
            # retains its existing DRF whitespace policy.
            fields["pppoe_pass"].trim_whitespace = False
        return fields

    def validate_customer_id(self, value):
        """
        Customer IDs are currently checked globally.

        This can later be changed to organization-scoped
        validation if required.
        """
        if (
            value
            and CustomerProfile.objects.filter(
                customer_id=value
            ).exists()
        ):
            raise serializers.ValidationError(
                "This customer ID is already in use."
            )

        return value

    def validate_pppoe_name(self, value):
        if value:
            return value.lower()

        return value

    def validate(self, attrs):
        """
        Validate the PPPoE fields based on authentication mode.

        local_secret:
            When a router is selected, PPPoE username and
            password must be supplied.

        radius:
            Router, package and operator password are required.
            Lintech generates the RADIUS username only.
        """
        authentication_mode = attrs.get(
            "authentication_mode",
            "local_secret",
        )

        router_id = attrs.get(
            "router_id"
        )

        package_id = attrs.get(
            "package_id"
        )

        if authentication_mode == "radius":
            if not router_id:
                raise serializers.ValidationError(
                    {
                        "router_id": (
                            "Router is required for a "
                            "RADIUS-managed PPPoE customer."
                        )
                    }
                )

            if not package_id:
                raise serializers.ValidationError(
                    {
                        "package_id": (
                            "Package is required for a "
                            "RADIUS-managed PPPoE customer."
                        )
                    }
                )

            if "pppoe_name" in attrs:
                raise serializers.ValidationError({
                    "pppoe_name": "RADIUS usernames are generated by Lintech; omit this field.",
                })

            password = attrs.get("pppoe_pass")
            if not password or not password.strip():
                raise serializers.ValidationError({
                    "pppoe_pass": "A non-empty PPPoE password is required for a RADIUS customer.",
                })

        elif authentication_mode == "local_secret":
            if router_id:
                if not attrs.get(
                    "pppoe_name"
                ):
                    raise serializers.ValidationError(
                        {
                            "pppoe_name": (
                                "PPPoE name is required when "
                                "a router is selected."
                            )
                        }
                    )

                if not attrs.get(
                    "pppoe_pass"
                ):
                    raise serializers.ValidationError(
                        {
                            "pppoe_pass": (
                                "PPPoE password is required "
                                "when a router is selected."
                            )
                        }
                    )

        return attrs


class CustomerLinkExistingSerializer(
    CustomerCreateSerializer
):
    """
    Serializer used when linking a Lintech customer to an
    already-existing MikroTik PPPoE secret.

    Existing-account linking remains local-secret only.
    """

    pppoe_name = serializers.CharField(
        max_length=255,
        required=True,
        write_only=True,
    )

    pppoe_pass = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        allow_null=True,
        write_only=True,
    )

    router_id = serializers.IntegerField(
        required=True,
        write_only=True,
    )

    authentication_mode = serializers.ChoiceField(
        choices=[
            (
                "local_secret",
                "Local MikroTik Secret",
            ),
        ],
        required=False,
        default="local_secret",
        write_only=True,
    )

    def validate(self, attrs):
        """
        Linking applies to an already-existing MikroTik
        local PPP secret.
        """
        attrs[
            "authentication_mode"
        ] = "local_secret"

        if not attrs.get(
            "router_id"
        ):
            raise serializers.ValidationError(
                {
                    "router_id": (
                        "Router is required when linking "
                        "an existing PPPoE customer."
                    )
                }
            )

        if not attrs.get(
            "pppoe_name"
        ):
            raise serializers.ValidationError(
                {
                    "pppoe_name": (
                        "PPPoE name is required when linking "
                        "an existing customer."
                    )
                }
            )

        return attrs


class CustomerListSerializer(
    serializers.ModelSerializer
):
    zone_name = serializers.CharField(
        source="zone.name",
        read_only=True,
    )

    package_name = serializers.CharField(
        source="package.name",
        read_only=True,
    )

    pppoe_name = serializers.SerializerMethodField()

    authentication_mode = serializers.SerializerMethodField()

    class Meta:
        model = CustomerProfile

        fields = [
            "id",
            "customer_id",
            "customer_name",
            "phone_number",
            "address",
            "customer_status",
            "zone",
            "zone_name",
            "package_name",
            "balance",
            "billing_date",
            "extended_billing_days",
            "pppoe_name",
            "authentication_mode",
            "created_at",
        ]

    def get_pppoe_name(self, obj):
        info = getattr(
            obj,
            "router_info",
            None,
        )

        return (
            info.pppoe_name
            if info
            else None
        )

    def get_authentication_mode(
        self,
        obj,
    ):
        info = getattr(
            obj,
            "router_info",
            None,
        )

        return (
            info.authentication_mode
            if info
            else None
        )


class CustomerDetailSerializer(
    serializers.ModelSerializer
):
    zone_name = serializers.CharField(
        source="zone.name",
        read_only=True,
    )

    package_name = serializers.CharField(
        source="package.name",
        read_only=True,
    )

    package_price = serializers.DecimalField(
        source="package.price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    router_info = serializers.SerializerMethodField()

    billing_summary = serializers.SerializerMethodField()

    class Meta:
        model = CustomerProfile

        fields = [
            "id",
            "customer_id",
            "customer_name",
            "nid",
            "phone_number",
            "phone_number2",
            "address",
            "zone",
            "package",
            "zone_name",
            "package_name",
            "package_price",
            "billing_date",
            "extended_billing_days",
            "customer_status",
            "balance",
            "router_info",
            "billing_summary",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "customer_id",
            "billing_date",
            "extended_billing_days",
            "customer_status",
            "balance",
            "created_at",
        ]

    def update(self, instance, validated_data):
        from customers.service import CustomerService

        return CustomerService.update_customer_profile(
            instance.organization,
            instance.customer_id,
            validated_data,
        )

    def validate_zone(
        self,
        value,
    ):
        """
        Prevent moving the customer into another
        organization's zone.
        """
        if (
            self.instance
            and value.organization_id
            != self.instance.organization_id
        ):
            raise serializers.ValidationError(
                "Zone does not belong to this organization."
            )

        return value

    def validate_package(
        self,
        value,
    ):
        """
        Prevent assigning another organization's package.
        """
        if (
            value
            and self.instance
            and value.organization_id
            != self.instance.organization_id
        ):
            raise serializers.ValidationError(
                "Package does not belong to this organization."
            )

        return value

    def get_router_info(
        self,
        obj,
    ):
        info = getattr(
            obj,
            "router_info",
            None,
        )

        if not info:
            return None

        return {
            "authentication_mode": (
                info.authentication_mode
            ),
            "pppoe_name": (
                info.pppoe_name
            ),
            "profile_name": (
                info.profile_name
            ),
            "remote_ip": (
                info.remote_ip
            ),
            "router": (
                info.router_id
            ),
            "router_name": (
                info.router.name
                if info.router
                else None
            ),
        }

    def get_billing_summary(
        self,
        obj,
    ):
        from billing.services import (
            BillingService,
        )

        return (
            BillingService
            .get_customer_billing_summary(
                obj.organization,
                obj.customer_id,
            )
        )