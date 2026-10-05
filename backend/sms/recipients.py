from customers.models import CustomerProfile


def _with_phone(queryset):
    return [
        (customer.phone_number, customer)
        for customer in queryset.select_related(
            "package",
            "zone",
        )
        if customer.phone_number
    ]


def resolve_recipients(
    organization,
    audience: str,
    payload: dict,
):
    """
    Return (mobile, customer-or-None) tuples belonging
    only to the supplied organization.
    """

    if audience == "single":
        number = payload.get(
            "mobile",
            "",
        )

        return [
            (number, None)
        ] if number else []

    if audience == "customer":
        customer = (
            CustomerProfile.objects
            .filter(
                organization=organization,
                customer_id=payload.get(
                    "customer_id"
                ),
            )
            .select_related(
                "package",
                "zone",
            )
            .first()
        )

        if (
            customer
            and customer.phone_number
        ):
            return [
                (
                    customer.phone_number,
                    customer,
                )
            ]

        return []

    queryset = (
        CustomerProfile.objects
        .filter(
            organization=organization
        )
    )

    if audience == "active":
        queryset = queryset.filter(
            customer_status="active"
        )

    elif audience == "inactive":
        queryset = queryset.filter(
            customer_status="disconnected"
        )

    elif audience == "zone":
        queryset = queryset.filter(
            zone_id=payload.get(
                "zone"
            )
        )

    elif audience in (
        "dues",
        "unpaid",
    ):
        queryset = queryset.filter(
            balance__lt=0
        )

    elif audience == "paid":
        queryset = queryset.filter(
            balance__gte=0
        )

    else:
        return []

    return _with_phone(
        queryset
    )