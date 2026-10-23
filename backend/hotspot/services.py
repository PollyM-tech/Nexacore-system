import hashlib
import secrets
import re
from datetime import timedelta
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from auditlog.services import AuditService
from radius.disconnect import queue_disconnect
from .models import Voucher, VoucherBatch, HotspotSession


SNAPSHOT_FIELDS = ('plan_name', 'price', 'duration_seconds', 'upload_kbps', 'download_kbps', 'quota_bytes')


def digest(code):
    return hashlib.sha256(code.encode()).hexdigest()


def snapshot(plan):
    return {'plan_name': plan.name, 'price': str(plan.price), 'duration_seconds': plan.duration_seconds,
            'upload_kbps': plan.upload_kbps, 'download_kbps': plan.download_kbps, 'quota_bytes': plan.quota_bytes}


@transaction.atomic
def issue_batch(plan, count, label='', redeem_before=None, entitlement=None):
    if not plan.is_active or not plan.organization.is_active or plan.organization.status != 'active':
        raise ValidationError('An active organization and plan are required.')
    batch = VoucherBatch.objects.create(organization=plan.organization, plan=plan, label=label)
    for _ in range(count):
        code = 'HS' + secrets.token_hex(16).upper()
        Voucher.objects.create(organization=plan.organization, batch=batch, code_hash=digest(code), code=code,
                               redeem_before=redeem_before, **(entitlement or snapshot(plan)))
    return batch


def mac_address(value):
    value = re.sub(r'[-:.]', '', str(value)).upper()
    if not re.fullmatch('[0-9A-F]{12}', value):
        raise ValidationError('A valid device MAC is required.')
    return ':'.join(value[i:i+2] for i in range(0, 12, 2))


def usage(voucher):
    values = voucher.sessions.aggregate(up=Sum('upload_bytes'), down=Sum('download_bytes'))
    return (values['up'] or 0) + (values['down'] or 0)


def usable(voucher, now):
    if voucher.status in ('revoked', 'expired', 'exhausted'):
        return False
    if not voucher.organization.is_active or voucher.organization.status != 'active':
        return False
    if voucher.expires_at and voucher.expires_at <= now:
        return False
    if not voucher.activated_at and voucher.redeem_before and voucher.redeem_before <= now:
        return False
    return not voucher.quota_bytes or usage(voucher) < voucher.quota_bytes


@transaction.atomic
def authorize(nas, username, mac, session_id):
    now = timezone.now()
    voucher = Voucher.objects.select_for_update().select_related('organization').filter(
        code_hash=digest(username), organization=nas.organization).first()
    if not nas.hotspot_enabled or not voucher or not usable(voucher, now):
        raise ValidationError('Voucher unavailable.')
    if not session_id or len(session_id) > 253:
        raise ValidationError('NAS must supply Acct-Session-Id during authentication.')
    mac = mac_address(mac)
    if voucher.bound_mac and voucher.bound_mac != mac:
        raise ValidationError('This voucher is bound to another device.')
    if voucher.reservation_until and voucher.reservation_until > now and (
            voucher.reserved_mac != mac or voucher.reserved_nas_id != nas.pk or voucher.reserved_session_id != session_id):
        raise ValidationError('Voucher authentication is in progress on another device.')
    # One concurrent device/session. Never allocate the same remaining quota twice.
    open_sessions = voucher.sessions.filter(stopped_at__isnull=True)
    if not voucher.quota_bytes:
        open_sessions = open_sessions.filter(disconnected_at__isnull=True)
    if open_sessions.exclude(nas=nas, session_id=session_id).exists():
        raise ValidationError('Voucher is active or awaiting final accounting. Retry after the NAS sends Accounting Stop.')
    voucher.reserved_session_id = session_id
    voucher.reserved_mac, voucher.reserved_nas, voucher.reservation_until = mac, nas, now + timedelta(seconds=20)
    voucher.save(update_fields=['reserved_mac', 'reserved_nas', 'reserved_session_id', 'reservation_until'])
    seconds = max(1, int((voucher.expires_at-now).total_seconds())) if voucher.expires_at else voucher.duration_seconds
    limits = {'control:Cleartext-Password': username, 'reply:Session-Timeout': seconds,
              'reply:Acct-Interim-Interval': 60,
              'reply:Mikrotik-Rate-Limit': f'{voucher.upload_kbps}k/{voucher.download_kbps}k',
              'reply:Port-Limit': 1}
    if voucher.quota_bytes:
        remaining = voucher.quota_bytes - usage(voucher)
        limits['reply:Mikrotik-Total-Limit'] = remaining % (2**32)
        limits['reply:Mikrotik-Total-Limit-Gigawords'] = remaining // (2**32)
    return limits


@transaction.atomic
def commit(nas, username, mac, session_id):
    now = timezone.now()
    voucher = Voucher.objects.select_for_update().select_related('organization').filter(
        code_hash=digest(username), organization=nas.organization).first()
    if not voucher or not usable(voucher, now):
        raise ValidationError('Voucher unavailable.')
    mac = mac_address(mac)
    if voucher.reserved_mac != mac or voucher.reserved_nas_id != nas.pk or voucher.reserved_session_id != session_id or not voucher.reservation_until or voucher.reservation_until < now:
        raise ValidationError('Authorization reservation expired.')
    if not voucher.activated_at:
        voucher.activated_at, voucher.expires_at = now, now + timedelta(seconds=voucher.duration_seconds)
        voucher.status = 'active'
        AuditService.log(organization=nas.organization, action='hotspot.voucher_activated', resource_type='Voucher',
                         resource_id=voucher.pk, metadata={'nas_id': nas.pk})
    voucher.bound_mac = mac
    voucher.save()
    session, _ = HotspotSession.objects.get_or_create(nas=nas, session_id=session_id, defaults={'voucher': voucher, 'mac': mac})
    if session.voucher_id != voucher.pk or session.mac != mac:
        raise ValidationError('Session identity mismatch.')


def disconnect_voucher(voucher, reason):
    for session in voucher.sessions.filter(stopped_at__isnull=True, disconnected_at__isnull=True).select_related('nas__organization'):
        queue_disconnect(session.nas, voucher.code, session.session_id, session.mac, reason)


@transaction.atomic
def revoke(voucher, request=None):
    voucher = Voucher.objects.select_for_update().get(pk=voucher.pk)
    voucher.status = 'revoked'
    voucher.save(update_fields=['status'])
    disconnect_voucher(voucher, 'revoked')
    AuditService.log(request=request, organization=voucher.organization, action='hotspot.voucher_revoked',
                     resource_type='Voucher', resource_id=voucher.pk)
    return voucher


@transaction.atomic
def account(nas, username, values):
    now = timezone.now()
    voucher = Voucher.objects.select_for_update().filter(code_hash=digest(username), organization=nas.organization).first()
    if not voucher or not voucher.activated_at:
        raise ValidationError('Unknown voucher accounting identity.')
    session_id = str(values.get('Acct-Session-Id', ''))
    if not session_id or len(session_id) > 253:
        raise ValidationError('Session ID required.')
    mac = mac_address(values.get('Calling-Station-Id', ''))
    if mac != voucher.bound_mac:
        raise ValidationError('Device mismatch.')
    kind = values.get('Acct-Status-Type')
    if kind not in ('Start', 'Interim-Update', 'Stop'):
        raise ValidationError('Unsupported accounting event.')
    session = HotspotSession.objects.filter(nas=nas, session_id=session_id).first()
    if session and (session.voucher_id != voucher.pk or session.mac != mac):
        raise ValidationError('Session identity mismatch.')
    if not session:
        raise ValidationError('Accounting must reference a successfully authenticated session.')
    if not session.started_at:
        elapsed = min(max(0, int(values.get('Acct-Session-Time', 0))), voucher.duration_seconds)
        session.started_at = now-timedelta(seconds=elapsed)
    def counter(octets, gigawords):
        low, high = int(values.get(octets, 0)), int(values.get(gigawords, 0))
        if low < 0 or low >= 2**32 or high < 0 or high >= 2**31:
            raise ValidationError('Invalid accounting counters.')
        return low + high * 2**32
    session.upload_bytes = max(session.upload_bytes, counter('Acct-Input-Octets', 'Acct-Input-Gigawords'))
    session.download_bytes = max(session.download_bytes, counter('Acct-Output-Octets', 'Acct-Output-Gigawords'))
    session.duration_seconds = max(session.duration_seconds, min(int(values.get('Acct-Session-Time', 0)), 2**31-1))
    session.updated_at = now
    session.ip = values.get('Framed-IP-Address') or session.ip
    if kind == 'Stop':
        session.stopped_at = session.stopped_at or now
        session.terminate_cause = str(values.get('Acct-Terminate-Cause', ''))[:100]
    session.save()
    voucher.reservation_until = now
    voucher.save(update_fields=['reservation_until'])
    if voucher.quota_bytes and usage(voucher) >= voucher.quota_bytes and voucher.status != 'revoked':
        voucher.status = 'exhausted'
        voucher.save(update_fields=['status'])
        disconnect_voucher(voucher, 'quota')
    elif voucher.status in ('revoked', 'expired') or voucher.expires_at <= now:
        disconnect_voucher(voucher, voucher.status if voucher.status in ('revoked', 'expired') else 'expired')


def enforce_limits():
    now = timezone.now()
    Voucher.objects.filter(status='unused', redeem_before__lte=now).update(status='expired')
    for voucher in Voucher.objects.filter(status='active').select_related('organization').iterator():
        with transaction.atomic():
            voucher = Voucher.objects.select_for_update().get(pk=voucher.pk)
            if voucher.status != 'active':
                continue
            reason = None
            if voucher.expires_at <= now:
                reason = 'expired'
            elif voucher.quota_bytes and usage(voucher) >= voucher.quota_bytes:
                reason = 'quota'
            elif not voucher.organization.is_active or voucher.organization.status != 'active':
                reason = 'suspended'
            if reason:
                if reason != 'suspended':
                    voucher.status = 'exhausted' if reason == 'quota' else 'expired'
                    voucher.save(update_fields=['status'])
                disconnect_voucher(voucher, reason)
