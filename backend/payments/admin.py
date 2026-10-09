from django.contrib import admin, messages

from .forms import MpesaConfigurationAdminForm
from .models import (
    C2BTransaction,
    MpesaConfiguration,
    PaymentAttempt,
)
from .services import DarajaClient, DarajaError


class LintechPlatformAdminMixin:
    """
    Payment infrastructure configuration is restricted to
    Lintech platform administrators.

    ISP tenant users must never manage Daraja configuration.
    """

    def _allowed(self, request):
        return (
            request.user.is_authenticated
            and request.user.is_superuser
        )

    def has_module_permission(self, request):
        return self._allowed(request)

    def has_view_permission(self, request, obj=None):
        return self._allowed(request)

    def has_add_permission(self, request):
        return self._allowed(request)

    def has_change_permission(self, request, obj=None):
        return self._allowed(request)

    def has_delete_permission(self, request, obj=None):
        return self._allowed(request)


@admin.register(MpesaConfiguration)
class MpesaConfigurationAdmin(
    LintechPlatformAdminMixin,
    admin.ModelAdmin,
):
    form = MpesaConfigurationAdminForm

    list_display = [
        "organization",
        "payment_mode",
        "service_scope",
        "shortcode",
        "transaction_type",
        "environment",
        "is_active",
        "is_default",
        "configured_by",
        "updated_at",
    ]

    list_filter = [
        "payment_mode",
        "service_scope",
        "environment",
        "transaction_type",
        "is_active",
        "is_default",
    ]

    search_fields = [
        "organization__name",
        "organization__slug",
        "shortcode",
    ]

    readonly_fields = [
        "callback_token",
        "configured_by",
        "created_at",
        "updated_at",
    ]

    actions = [
        "test_daraja_credentials",
    ]

    fieldsets = (
        (
            "ISP",
            {
                "fields": (
                    "organization",
                    "service_scope",
                    "payment_mode",
                )
            },
        ),
        (
            "M-Pesa Business Account",
            {
                "fields": (
                    "shortcode",
                    "transaction_type",
                    "environment",
                )
            },
        ),
        (
            "Daraja Credentials",
            {
                "description": (
                    "Existing credentials are never displayed. "
                    "When editing, leave a secret field blank "
                    "to preserve the current encrypted value."
                ),
                "fields": (
                    "consumer_key",
                    "consumer_secret",
                    "passkey",
                ),
            },
        ),
        (
            "Configuration",
            {
                "fields": (
                    "is_active",
                    "is_default",
                    "callback_token",
                    "notes",
                )
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "configured_by",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        if obj.configured_by_id is None:
            obj.configured_by = request.user

        super().save_model(
            request,
            obj,
            form,
            change,
        )

    @admin.action(
        description="Test selected Daraja credentials"
    )
    def test_daraja_credentials(
        self,
        request,
        queryset,
    ):
        """
        Test OAuth authentication against Safaricom Daraja.

        Access tokens and credentials are never displayed.
        """

        for configuration in queryset.select_related(
            "organization"
        ):
            try:
                result = DarajaClient(
                    configuration
                ).test_connection()

            except DarajaError as exc:
                self.message_user(
                    request,
                    (
                        f"{configuration.organization.name}: "
                        f"{exc}"
                    ),
                    level=messages.ERROR,
                )
                continue

            except Exception:
                self.message_user(
                    request,
                    (
                        f"{configuration.organization.name}: "
                        "Unexpected error while testing Daraja."
                    ),
                    level=messages.ERROR,
                )
                continue

            self.message_user(
                request,
                (
                    f"{configuration.organization.name}: "
                    "Daraja authentication successful "
                    f"({result['environment']})."
                ),
                level=messages.SUCCESS,
            )


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(
    LintechPlatformAdminMixin,
    admin.ModelAdmin,
):
    list_display = [
        "id",
        "organization",
        "customer",
        "amount",
        "purpose",
        "status",
        "settlement_status",
        "provisioning_status",
        "mpesa_receipt_number",
        "created_at",
    ]

    list_filter = [
        "service_type",
        "purpose",
        "status",
        "settlement_status",
        "provisioning_status",
    ]

    search_fields = [
        "checkout_request_id",
        "merchant_request_id",
        "mpesa_receipt_number",
        "account_reference",
        "customer__customer_id",
        "customer__customer_name",
    ]

    readonly_fields = [
        "organization",
        "payment_configuration",
        "customer",
        "monthly_bill",
        "connection_fee",
        "target_package",
        "payment_transaction",
        "service_type",
        "purpose",
        "phone_number",
        "amount",
        "account_reference",
        "merchant_request_id",
        "checkout_request_id",
        "mpesa_receipt_number",
        "status",
        "settlement_status",
        "provisioning_status",
        "result_code",
        "result_description",
        "transaction_date",
        "reconciled_at",
        "completed_at",
        "created_at",
        "updated_at",
    ]

    exclude = [
        "callback_payload",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return self.has_view_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(C2BTransaction)
class C2BTransactionAdmin(
    LintechPlatformAdminMixin,
    admin.ModelAdmin,
):
    list_display = [
        "trans_id",
        "organization",
        "customer",
        "amount",
        "bill_ref_number",
        "allocation_status",
        "received_at",
    ]

    list_filter = [
        "allocation_status",
    ]

    search_fields = [
        "trans_id",
        "bill_ref_number",
        "organization__name",
        "customer__customer_id",
        "customer__customer_name",
    ]

    readonly_fields = [
        "organization",
        "payment_configuration",
        "customer",
        "payment_transaction",
        "trans_id",
        "bill_ref_number",
        "amount",
        "business_shortcode",
        "allocation_status",
        "received_at",
        "allocated_at",
        "created_at",
        "updated_at",
    ]

    exclude = [
        "raw_payload",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return self.has_view_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False