from rest_framework import serializers

from .models import (
    OltDevice,
    Onu,
)


class OltDeviceSerializer(
    serializers.ModelSerializer
):
    onu_count = serializers.IntegerField(
        source="onus.count",
        read_only=True,
    )

    telnet_password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        trim_whitespace=False,
    )

    snmp_community = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=False,
        trim_whitespace=False,
    )

    class Meta:
        model = OltDevice

        fields = [
            "id",
            "name",
            "host",
            "telnet_port",
            "web_port",
            "protocol",
            "olt_type",
            "vendor",
            "pon_type",
            "telnet_username",
            "telnet_password",
            "snmp_port",
            "snmp_community",
            "timeout",
            "status",
            "last_checked",
            "description",
            "is_active",
            "onu_count",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "vendor",
            "pon_type",
            "status",
            "last_checked",
            "created_at",
        ]


class OnuSerializer(
    serializers.ModelSerializer
):
    olt_name = serializers.CharField(
        source="olt.name",
        read_only=True,
    )

    customer_name = serializers.CharField(
        source="customer.customer_name",
        read_only=True,
    )

    customer_code = serializers.CharField(
        source="customer.customer_id",
        read_only=True,
    )

    class Meta:
        model = Onu

        fields = [
            "id",
            "olt",
            "olt_name",
            "onu_index",
            "serial_number",
            "name",
            "pon_port",
            "onu_model",
            "status",
            "rx_power",
            "tx_power",
            "olt_rx_power",
            "distance",
            "customer",
            "customer_name",
            "customer_code",
            "last_seen",
            "description",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "last_seen",
            "created_at",
        ]

    def validate(self, attrs):
        from organizations.services import get_user_organization
        organization = get_user_organization(self.context["request"].user)
        olt = attrs.get("olt", self.instance.olt if self.instance else None)
        customer = attrs.get("customer", self.instance.customer if self.instance else None)
        if olt is None or olt.organization_id != organization.pk:
            raise serializers.ValidationError({"olt": "Select an OLT in your organization."})
        if customer is not None and customer.organization_id != organization.pk:
            raise serializers.ValidationError({"customer": "Select a customer in your organization."})
        return attrs
