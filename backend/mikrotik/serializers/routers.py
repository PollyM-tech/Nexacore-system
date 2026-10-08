from rest_framework import serializers

from mikrotik.models import (
    MikrotikRouter,
    RouterInfo,
)


class MikrotikRouterSerializer(
    serializers.ModelSerializer
):
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=False,
        trim_whitespace=False,
    )

    class Meta:
        model = MikrotikRouter

        fields = [
            "id",
            "name",
            "host",
            "port",
            "username",
            "password",
            "use_ssl",
            "status",
            "last_checked",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "created_at",
            "updated_at",
            "last_checked",
            "status",
        ]

    def validate(
        self,
        attrs,
    ):
        if (
            self.instance is None
            and not attrs.get(
                "password"
            )
        ):
            raise (
                serializers.ValidationError(
                    {
                        "password": (
                            "Router password "
                            "is required."
                        )
                    }
                )
            )

        return attrs


class RouterInfoSerializer(
    serializers.ModelSerializer
):
    customer_id = (
        serializers.CharField(
            source=(
                "customer.customer_id"
            ),
            read_only=True,
        )
    )

    router_name = (
        serializers.CharField(
            source="router.name",
            read_only=True,
        )
    )

    pppoe_pass = (
        serializers.CharField(
            write_only=True,
            required=False,
            allow_blank=False,
            trim_whitespace=False,
        )
    )

    class Meta:
        model = RouterInfo

        fields = [
            "id",
            "pppoe_name",
            "pppoe_pass",
            "profile_name",
            "remote_ip",
            "customer",
            "customer_id",
            "router",
            "router_name",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "created_at",
            "updated_at",
        ]

    def validate(
        self,
        attrs,
    ):
        if (
            self.instance is None
            and not attrs.get(
                "pppoe_pass"
            )
        ):
            raise (
                serializers.ValidationError(
                    {
                        "pppoe_pass": (
                            "PPPoE password "
                            "is required."
                        )
                    }
                )
            )

        return attrs