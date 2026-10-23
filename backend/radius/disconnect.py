"""RFC 5176 Disconnect-Request; no shell commands, RouterOS credentials or packet logs."""
import hashlib
import hmac
import secrets
import socket
import struct
from datetime import timedelta
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from auditlog.services import AuditService
from .models import DisconnectRequest, DisconnectAttempt, NasDevice, RadAcct


class InvalidResponse(Exception):
    pass


def attribute(kind, value):
    if len(value) > 253:
        raise ValueError('Attribute too long.')
    return bytes([kind, len(value) + 2]) + value


def packet(username, session_id, nas_ip, secret, caller_id='', *, identifier=None, timestamp=None):
    identifier = secrets.randbelow(256) if identifier is None else identifier
    timestamp = int(timezone.now().timestamp()) if timestamp is None else timestamp
    attrs = attribute(1, username.encode()) + attribute(44, session_id.encode())
    attrs += attribute(4, socket.inet_aton(nas_ip)) + attribute(55, struct.pack('!I', timestamp))
    if caller_id:
        attrs += attribute(31, caller_id.encode())
    attrs += attribute(80, bytes(16))
    header = struct.pack('!BBH', 40, identifier, 20 + len(attrs))
    message_auth = hmac.new(secret.encode(), header + bytes(16) + attrs, hashlib.md5).digest()
    attrs = attrs[:-16] + message_auth
    authenticator = hashlib.md5(header + bytes(16) + attrs + secret.encode()).digest()
    return header + authenticator + attrs


def parse_response(data, request, secret):
    if len(data) < 20:
        raise InvalidResponse()
    code, identifier, length = struct.unpack('!BBH', data[:4])
    if code not in (41, 42) or identifier != request[1] or length != len(data):
        raise InvalidResponse()
    expected = hashlib.md5(data[:4] + request[4:20] + data[20:] + secret.encode()).digest()
    if not hmac.compare_digest(expected, data[4:20]):
        raise InvalidResponse()
    cause, offset, ma_seen = None, 20, False
    while offset < length:
        if offset + 2 > length or data[offset+1] < 2 or offset + data[offset+1] > length:
            raise InvalidResponse()
        kind, size = data[offset:offset+2]
        if kind == 101:
            if size != 6:
                raise InvalidResponse()
            cause = struct.unpack('!I', data[offset+2:offset+6])[0]
        if kind == 80:
            if ma_seen or size != 18:
                raise InvalidResponse()
            ma_seen = True
            zeroed = data[:4] + request[4:20] + data[20:offset+2] + bytes(16) + data[offset+18:]
            if not hmac.compare_digest(hmac.new(secret.encode(), zeroed, hashlib.md5).digest(), data[offset+2:offset+18]):
                raise InvalidResponse()
        offset += size
    return ('ack' if code == 41 else 'nak'), cause


def transmit(request):
    nas = request.nas
    payload = packet(request.username, request.session_id, nas.source_ip, nas.shared_secret, request.caller_id)
    # Connected UDP socket also rejects responses from another IP/port.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(3)
        sock.connect((nas.source_ip, nas.disconnect_port))
        sock.send(payload)
        return parse_response(sock.recv(4096), payload, nas.shared_secret)


def queue_disconnect(nas, username, session_id, caller_id='', reason='operator', request=None):
    if not session_id or not username:
        raise ValueError('A specific session is required.')
    item, created = DisconnectRequest.objects.get_or_create(
        nas=nas, username_hash=hashlib.sha256(username.encode()).hexdigest(), session_id=session_id, reason=reason,
        defaults={'username': username, 'caller_id': caller_id})
    if created:
        AuditService.log(request=request, organization=nas.organization, action='radius.disconnect_queued',
                         resource_type='DisconnectRequest', resource_id=item.pk,
                         metadata={'nas_id': nas.pk, 'reason': reason})
        def enqueue():
            # The periodic worker is the durable fallback if the broker is temporarily unavailable.
            try:
                from django_q.tasks import async_task
                async_task('radius.disconnect.process_request', item.pk)
            except Exception:
                pass
        transaction.on_commit(enqueue)
    return item


def queue_customer(customer, reason='suspended'):
    info = getattr(customer, 'router_info', None)
    nas = NasDevice.objects.filter(router_id=info.router_id, organization=customer.organization).first() if info else None
    if not nas:
        return False
    from .services import RadiusProvisioningService
    username = RadiusProvisioningService.build_radius_username(customer)
    for row in RadAcct.objects.filter(username=username, nasipaddress=nas.source_ip, acctstoptime__isnull=True):
        queue_disconnect(nas, username, row.acctsessionid, row.callingstationid or '', reason)
    return True


def process_request(pk):
    now = timezone.now()
    with transaction.atomic():
        item = DisconnectRequest.objects.select_for_update().select_related('nas__organization').get(pk=pk)
        if item.status in ('acknowledged', 'not_found', 'failed'):
            return
        if item.status == 'processing' and item.claimed_at and item.claimed_at > now - timedelta(seconds=45):
            return
        if item.next_attempt_at > now:
            return
        if item.attempts >= item.max_attempts:
            item.status = 'failed'
            item.save(update_fields=['status', 'updated_at'])
            return
        item.status, item.claimed_at = 'processing', now
        item.attempts += 1
        item.save(update_fields=['status', 'claimed_at', 'attempts', 'updated_at'])
    try:
        result, cause = transmit(item)
    except socket.timeout:
        result, cause = 'timeout', None
    except InvalidResponse:
        result, cause = 'invalid_response', None
    except (OSError, ValueError):
        result, cause = 'transport_error', None
    with transaction.atomic():
        current = DisconnectRequest.objects.select_for_update().get(pk=pk)
        if current.attempts != item.attempts or current.status != 'processing':
            return
        DisconnectAttempt.objects.create(request=current, number=current.attempts, result=result, error_cause=cause)
        if result == 'ack':
            current.status, current.acknowledged_at = 'acknowledged', timezone.now()
        elif result == 'nak':
            current.status = 'not_found' if cause == 503 else 'failed'
        else:
            current.status = 'retry' if current.attempts < current.max_attempts else 'failed'
        current.last_error = '' if result == 'ack' else result
        current.next_attempt_at = timezone.now() + timedelta(seconds=min(30 * 2 ** min(current.attempts - 1, 10), 600))
        current.save()
        if current.status in ('acknowledged', 'not_found'):
            from hotspot.models import HotspotSession
            HotspotSession.objects.filter(nas=item.nas, session_id=item.session_id, voucher__code_hash=item.username_hash, disconnected_at__isnull=True).update(disconnected_at=timezone.now())
        AuditService.log(organization=item.nas.organization, action='radius.disconnect_' + result,
                         resource_type='DisconnectRequest', resource_id=current.pk,
                         metadata={'nas_id': item.nas_id, 'attempt': current.attempts, 'error_cause': cause, 'status': current.status})


def retry_disconnects():
    now = timezone.now()
    due = DisconnectRequest.objects.filter(next_attempt_at__lte=now).filter(
        Q(status__in=['pending', 'retry']) | Q(status='processing', claimed_at__lt=now-timedelta(seconds=45)))
    for pk in due.order_by('next_attempt_at').values_list('pk', flat=True)[:10]:
        process_request(pk)
