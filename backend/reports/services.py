from datetime import date, timedelta

from django.db.models import Count, Q, Sum

from billing.models import (
    ConnectionFee,
    MonthlyBill,
    Package,
    PaymentTransaction,
)
from customers.models import CustomerProfile, SupportTicket
from mikrotik.models import MikrotikRouter


def _f(value):
    return float(value or 0)


class ReportService:
    """Organization-scoped analytics for the admin dashboard."""

    @staticmethod
    def _revenue_totals(organization):
        bill = MonthlyBill.objects.filter(
            customer__organization=organization
        ).aggregate(
            billed=Sum("total_amount"),
            collected=Sum("paid_amount"),
        )

        fee = ConnectionFee.objects.filter(
            customer__organization=organization
        ).aggregate(
            billed=Sum("total_amount"),
            collected=Sum("paid_amount"),
        )

        billed = _f(bill["billed"]) + _f(fee["billed"])
        collected = _f(bill["collected"]) + _f(fee["collected"])
        outstanding = billed - collected

        rate = round((collected / billed) * 100) if billed else 0

        return {
            "billed": billed,
            "collected": collected,
            "outstanding": outstanding,
            "collection_rate": rate,
        }

    @staticmethod
    def _monthly(organization, year):
        rows = (
            MonthlyBill.objects.filter(
                customer__organization=organization,
                billing_year=year,
            )
            .values("billing_month")
            .annotate(
                billed=Sum("total_amount"),
                collected=Sum("paid_amount"),
            )
        )

        table = {
            row["billing_month"]: row
            for row in rows
        }

        output = []

        for month in range(1, 13):
            row = table.get(month, {})

            billed = _f(row.get("billed"))
            collected = _f(row.get("collected"))

            output.append(
                {
                    "month": month,
                    "billed": billed,
                    "collected": collected,
                    "due": billed - collected,
                }
            )

        return output

    @staticmethod
    def _yearly(organization):
        rows = (
            MonthlyBill.objects.filter(
                customer__organization=organization
            )
            .values("billing_year")
            .annotate(
                billed=Sum("total_amount"),
                collected=Sum("paid_amount"),
            )
            .order_by("billing_year")
        )

        return [
            {
                "year": row["billing_year"],
                "billed": _f(row["billed"]),
                "collected": _f(row["collected"]),
            }
            for row in rows
        ]

    @staticmethod
    def _customer_breakdown(organization):
        today = date.today()

        customers = CustomerProfile.objects.filter(
            organization=organization
        )

        agg = customers.aggregate(
            total=Count("id"),
            active=Count(
                "id",
                filter=Q(customer_status="active"),
            ),
            disconnected=Count(
                "id",
                filter=Q(customer_status="disconnected"),
            ),
            free=Count(
                "id",
                filter=Q(customer_status="free"),
            ),
            left=Count(
                "id",
                filter=Q(customer_status="left"),
            ),
            due=Count(
                "id",
                filter=Q(balance__lt=0),
            ),
        )

        expired = 0
        expire_today = 0

        for customer in customers.exclude(
            customer_status="left"
        ).only(
            "billing_date",
            "extended_billing_days",
        ):
            if not customer.billing_date:
                continue

            due_date = customer.billing_date + timedelta(
                days=customer.extended_billing_days or 0
            )

            if due_date < today:
                expired += 1
            elif due_date == today:
                expire_today += 1

        agg["expired"] = expired
        agg["expire_today"] = expire_today

        return agg

    @staticmethod
    def _revenue_today(organization):
        agg = PaymentTransaction.objects.filter(
            customer__organization=organization,
            created_at__date=date.today(),
        ).aggregate(
            total=Sum("amount")
        )

        return _f(agg["total"])

    @staticmethod
    def dashboard_summary(organization):
        customers = ReportService._customer_breakdown(
            organization
        )

        tickets = SupportTicket.objects.filter(
            customer__organization=organization
        ).aggregate(
            total=Count("id"),
            open=Count(
                "id",
                filter=Q(status="open"),
            ),
            in_progress=Count(
                "id",
                filter=Q(status="in_progress"),
            ),
            resolved=Count(
                "id",
                filter=Q(status="resolved"),
            ),
            closed=Count(
                "id",
                filter=Q(status="closed"),
            ),
        )

        packages = Package.objects.filter(
            organization=organization
        )

        routers = MikrotikRouter.objects.filter(
            organization=organization
        )

        return {
            "customers": customers,
            "packages": {
                "total": packages.count(),
                "active": packages.filter(
                    is_active=True
                ).count(),
            },
            "routers": {
                "total": routers.count(),
                "active": routers.filter(
                    is_active=True
                ).count(),
            },
            "tickets": tickets,
            "revenue": {
                **ReportService._revenue_totals(
                    organization
                ),
                "today": ReportService._revenue_today(
                    organization
                ),
            },
            "monthly": ReportService._monthly(
                organization,
                date.today().year,
            ),
            "yearly": ReportService._yearly(
                organization
            ),
        }