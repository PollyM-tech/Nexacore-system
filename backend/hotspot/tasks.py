def network_access_maintenance():
    from hotspot.services import enforce_limits
    from radius.disconnect import retry_disconnects
    from payments.models import PaymentAttempt
    from payments.tasks import process_successful_stk_payment
    enforce_limits()
    retry_disconnects()
    for pk in PaymentAttempt.objects.filter(service_type='hotspot', status='successful').exclude(provisioning_status='provisioned').values_list('pk', flat=True)[:5]:
        process_successful_stk_payment(pk)
