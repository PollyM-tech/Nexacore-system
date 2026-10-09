from payments.services import (
    PaymentProvisioningService,
    PaymentSettlementService,
)


def process_successful_stk_payment(
    attempt_id,
):
    """
    Process a Safaricom-confirmed STK payment.

    Stage 1:
        Settle the payment into Lintech billing.

    Stage 2:
        Provision/reactivate the customer's service.

    Router failure does not undo settlement or renewal.
    Failed provisioning is retried later by the scheduled
    provisioning retry job.
    """

    result = {
        "attempt_id": attempt_id,
        "settled": False,
        "provisioned": False,
        "error": None,
    }

    # ---------------------------------------------------------
    # Settlement
    # ---------------------------------------------------------

    try:
        PaymentSettlementService.settle_stk_attempt(
            attempt_id
        )

        result["settled"] = True

    except Exception as exc:
        result["error"] = (
            f"Settlement failed: {exc}"
        )

        return result

    # ---------------------------------------------------------
    # Provisioning
    # ---------------------------------------------------------

    try:
        PaymentProvisioningService.provision_stk_attempt(
            attempt_id
        )

        result["provisioned"] = True

    except Exception as exc:
        # Payment remains settled.
        #
        # PaymentProvisioningService records failed
        # provisioning, and the hourly scheduler will
        # retry it later.
        result["error"] = (
            f"Provisioning failed: {exc}"
        )

    return result