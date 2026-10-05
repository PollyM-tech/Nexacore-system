from datetime import timedelta

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import serializers

from billing.models import (
    ConnectionFee,
    InvoiceStatusHistory,
    MonthlyBill,
    PaymentAllocation,
    PaymentTransaction,
)
from customers.models import CustomerProfile


class BillingService:
    @staticmethod
    def _get_customer(organization, customer_id):
        """
        Return a customer only when they belong to the supplied organization.
        """
        try:
            return CustomerProfile.objects.get(
                organization=organization,
                customer_id=customer_id,
            )
        except CustomerProfile.DoesNotExist:
            return None

    @staticmethod
    def create_monthly_bills(
        organization,
        target_month=None,
        target_year=None,
    ):
        """
        Generate monthly bills only for customers in one organization.
        """
        today = timezone.localtime().date()

        if not target_month:
            target_month = today.month

        if not target_year:
            target_year = today.year

        active_customers = (
            CustomerProfile.objects
            .filter(
                organization=organization,
                customer_status="active",
                package__isnull=False,
            )
            .select_related("package")
        )

        created_bills = []

        for customer in active_customers:
            existing_bill = MonthlyBill.objects.filter(
                customer=customer,
                billing_month=target_month,
                billing_year=target_year,
            ).exists()

            if existing_bill:
                continue

            package = customer.package

            if not package:
                continue

            bill = MonthlyBill.objects.create(
                customer=customer,
                package_name=package.name,
                package_price=package.price,
                billing_month=target_month,
                billing_year=target_year,
                invoice_date=today,
                total_amount=package.price,
                paid_amount=0,
            )

            created_bills.append(bill)

        return created_bills

    @staticmethod
    def create_specific_monthly_bill(
        organization,
        customer_id,
        billing_month,
        billing_year,
        notes="",
    ):
        """
        Generate one monthly bill for a customer in the organization.
        """
        customer = BillingService._get_customer(
            organization,
            customer_id,
        )

        if not customer:
            return {
                "status": "error",
                "message": "Customer not found",
            }

        if not customer.package:
            return {
                "status": "error",
                "message": "Customer has no package assigned",
            }

        existing_bill = MonthlyBill.objects.filter(
            customer=customer,
            billing_month=billing_month,
            billing_year=billing_year,
        ).exists()

        if existing_bill:
            return {
                "status": "error",
                "message": "Bill already exists for this month",
            }

        bill = MonthlyBill.objects.create(
            customer=customer,
            package_name=customer.package.name,
            package_price=customer.package.price,
            billing_month=billing_month,
            billing_year=billing_year,
            invoice_date=timezone.localtime().date(),
            total_amount=customer.package.price,
            paid_amount=0,
            notes=notes,
        )

        return {
            "status": "success",
            "message": "Monthly bill created successfully",
            "bill": bill,
        }

    @staticmethod
    def create_connection_fee(
        organization,
        customer_id,
        total_amount,
        notes="",
    ):
        """
        Create a connection fee only for a customer in the organization.
        """
        customer = BillingService._get_customer(
            organization,
            customer_id,
        )

        if not customer:
            return {
                "status": "error",
                "message": "Customer not found",
            }

        fee = ConnectionFee.objects.create(
            customer=customer,
            invoice_date=timezone.localtime().date(),
            total_amount=total_amount,
            paid_amount=0,
            notes=notes,
        )

        return {
            "status": "success",
            "message": "Connection fee created successfully",
            "fee": fee,
        }

    @staticmethod
    def check_overdue_bills(organization=None):
        """
        Mark overdue customers as disconnected.

        When organization is supplied, process one ISP only.

        When organization is None, process all organizations. This keeps the
        method usable by trusted background scheduler jobs.
        """
        today = timezone.localtime().date()

        overdue_customers = []

        unpaid_bills = MonthlyBill.objects.filter(
            payment_status__in=[
                "unpaid",
                "partial",
            ]
        ).filter(
            Q(billing_year__lt=today.year)
            | Q(
                billing_year=today.year,
                billing_month__lt=today.month,
            )
        )

        if organization is not None:
            unpaid_bills = unpaid_bills.filter(
                customer__organization=organization
            )

        unpaid_bills = unpaid_bills.select_related(
            "customer"
        )

        for bill in unpaid_bills:
            customer = bill.customer

            if customer.customer_status != "active":
                continue

            if not customer.billing_date:
                continue

            extended_date = (
                customer.billing_date
                + timedelta(
                    days=customer.extended_billing_days
                )
            )

            if today > extended_date:
                customer.customer_status = "disconnected"

                customer.save(
                    update_fields=[
                        "customer_status",
                        "updated_at",
                    ]
                )

                overdue_customers.append(
                    customer
                )

        return overdue_customers

    @staticmethod
    def get_customer_billing_summary(
        organization,
        customer_id,
    ):
        """
        Return billing totals for one customer within one organization.
        """
        monthly_bills = MonthlyBill.objects.filter(
            customer__organization=organization,
            customer__customer_id=customer_id,
        )

        connection_fees = ConnectionFee.objects.filter(
            customer__organization=organization,
            customer__customer_id=customer_id,
        )

        total_monthly = (
            monthly_bills.aggregate(
                total=Sum("total_amount")
            )["total"]
            or 0
        )

        total_fees = (
            connection_fees.aggregate(
                total=Sum("total_amount")
            )["total"]
            or 0
        )

        total_billed = (
            total_monthly
            + total_fees
        )

        paid_monthly = (
            monthly_bills.aggregate(
                total=Sum("paid_amount")
            )["total"]
            or 0
        )

        paid_fees = (
            connection_fees.aggregate(
                total=Sum("paid_amount")
            )["total"]
            or 0
        )

        total_paid = (
            paid_monthly
            + paid_fees
        )

        pending = (
            total_billed
            - total_paid
        )

        return {
            "total_billed": total_billed,
            "total_paid": total_paid,
            "pending_amount": pending,
            "monthly_bill_count": monthly_bills.count(),
            "connection_fee_count": connection_fees.count(),
        }

    @staticmethod
    @transaction.atomic
    def add_payment_transaction(
        organization,
        customer_id,
        amount,
        payment_method,
        transaction_id=None,
        received_by=None,
        notes="",
    ):
        """
        Record and allocate a payment for a customer in one organization.

        The customer row is locked while allocation takes place so concurrent
        payments cannot corrupt the balance.
        """
        try:
            customer = (
                CustomerProfile.objects
                .select_for_update()
                .get(
                    organization=organization,
                    customer_id=customer_id,
                )
            )
        except CustomerProfile.DoesNotExist:
            raise serializers.ValidationError(
                {
                    "customer_id": [
                        "Customer not found."
                    ]
                }
            )

        if amount == 0:
            raise serializers.ValidationError(
                {
                    "amount": [
                        "Amount cannot be zero."
                    ]
                }
            )

        transaction_obj = PaymentTransaction.objects.create(
            customer=customer,
            amount=amount,
            payment_method=payment_method,
            transaction_id=transaction_id or None,
            received_by=received_by,
            notes=notes or "",
        )

        customer.balance += amount

        customer.save(
            update_fields=[
                "balance",
                "updated_at",
            ]
        )

        # Negative payments represent manual debits/adjustments.
        # They affect the balance but should not settle invoices.
        if amount < 0:
            return transaction_obj

        connection_fees = (
            ConnectionFee.objects
            .select_for_update()
            .filter(
                customer=customer,
                payment_status__in=[
                    "unpaid",
                    "partial",
                ],
            )
            .order_by("created_at")
        )

        for fee in connection_fees:
            if customer.balance <= 0:
                break

            remaining = fee.remaining_amount

            allocate_amount = min(
                customer.balance,
                remaining,
            )

            if allocate_amount <= 0:
                continue

            PaymentAllocation.objects.create(
                payment_transaction=transaction_obj,
                connection_fee=fee,
                amount=allocate_amount,
            )

            previous_status = fee.payment_status

            fee.paid_amount += allocate_amount

            if fee.paid_amount >= fee.total_amount:
                fee.paid_amount = fee.total_amount
                fee.payment_status = "paid"
                fee.payment_date = timezone.localdate()
            else:
                fee.payment_status = "partial"

            fee.save(
                update_fields=[
                    "paid_amount",
                    "payment_status",
                    "payment_date",
                    "updated_at",
                ]
            )

            InvoiceStatusHistory.objects.create(
                connection_fee=fee,
                payment_transaction=transaction_obj,
                amount=allocate_amount,
                previous_status=previous_status,
                new_status=fee.payment_status,
            )

            customer.balance -= allocate_amount

            customer.save(
                update_fields=[
                    "balance",
                    "updated_at",
                ]
            )

        monthly_bills = (
            MonthlyBill.objects
            .select_for_update()
            .filter(
                customer=customer,
                payment_status__in=[
                    "unpaid",
                    "partial",
                ],
            )
            .order_by(
                "billing_year",
                "billing_month",
                "created_at",
            )
        )

        for bill in monthly_bills:
            if customer.balance <= 0:
                break

            remaining = bill.remaining_amount

            allocate_amount = min(
                customer.balance,
                remaining,
            )

            if allocate_amount <= 0:
                continue

            PaymentAllocation.objects.create(
                payment_transaction=transaction_obj,
                monthly_bill=bill,
                amount=allocate_amount,
            )

            previous_status = bill.payment_status

            bill.paid_amount += allocate_amount

            if bill.paid_amount >= bill.total_amount:
                bill.paid_amount = bill.total_amount
                bill.payment_status = "paid"
                bill.payment_date = timezone.localdate()
            else:
                bill.payment_status = "partial"

            bill.save(
                update_fields=[
                    "paid_amount",
                    "payment_status",
                    "payment_date",
                    "updated_at",
                ]
            )

            InvoiceStatusHistory.objects.create(
                monthly_bill=bill,
                payment_transaction=transaction_obj,
                amount=allocate_amount,
                previous_status=previous_status,
                new_status=bill.payment_status,
            )

            customer.balance -= allocate_amount

            customer.save(
                update_fields=[
                    "balance",
                    "updated_at",
                ]
            )

        return transaction_obj