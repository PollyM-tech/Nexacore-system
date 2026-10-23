"""Private FreeRADIUS REST bridge. Never routed through the public reverse proxy."""
import hmac
import ipaddress
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from django.utils import timezone
from .models import NasDevice, RadiusCheck, RadiusReply


class IsRadiusBridge(BasePermission):
    def has_permission(self, request, view):
        configured = getattr(settings, 'RADIUS_INTERNAL_TOKEN', '')
        supplied = request.headers.get('X-Lintech-Radius-Key', '')
        return len(configured) >= 32 and hmac.compare_digest(configured, supplied)


def values(data):
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            value = value.get('value', [])
        if isinstance(value, list):
            value = value[0] if value else ''
        result[key] = value
    return result


def radius_json(attrs):
    # Never expand response data as unlang/xlat (voucher/password characters are data).
    return {key: {'value': [value], 'op': ':=', 'do_xlat': False} for key, value in attrs.items()}


class RadiusBridge(APIView):
    authentication_classes = []
    permission_classes = [IsRadiusBridge]

    def finalize_response(self, request, response, *args, **kwargs):
        response['Cache-Control'] = 'no-store'
        return super().finalize_response(request, response, *args, **kwargs)

    def get_nas(self, ip):
        try:
            ipaddress.IPv4Address(ip)
        except ValueError:
            raise PermissionDenied('Invalid NAS source identity.') from None
        nas = NasDevice.objects.select_related('organization').filter(source_ip=ip, is_active=True,
            organization__is_active=True, organization__status='active').first()
        if not nas:
            raise PermissionDenied('Unknown NAS.')
        return nas

    def get(self, request, ip, operation):
        if operation != 'client':
            raise PermissionDenied()
        nas = self.get_nas(ip)
        return Response(radius_json({'control:FreeRADIUS-Client-IP-Address': nas.source_ip,
            'control:FreeRADIUS-Client-Secret': nas.shared_secret,
            'control:FreeRADIUS-Client-Shortname': f'lintech-nas-{nas.pk}',
            'control:FreeRADIUS-Client-NAS-Type': 'mikrotik',
            'control:FreeRADIUS-Client-Virtual-Server': 'lintech',
            'control:FreeRADIUS-Client-Require-MA': 'yes'}))

    def post(self, request, ip, operation):
        nas = self.get_nas(ip)
        attrs = values(request.data)
        if str(attrs.get('NAS-IP-Address', '')) != nas.source_ip:
            raise PermissionDenied('NAS source identity mismatch.')
        if nas.identifier and attrs.get('NAS-Identifier') != nas.identifier:
            raise PermissionDenied('NAS identifier mismatch.')
        if operation == 'accounting' and attrs.get('Acct-Status-Type') in ('Accounting-On', 'Accounting-Off'):
            from hotspot.models import HotspotSession
            HotspotSession.objects.filter(nas=nas, stopped_at__isnull=True).update(disconnected_at=timezone.now())
            return Response(status=204)
        username = str(attrs.get('User-Name', ''))
        if not username or len(username) > 253:
            raise PermissionDenied()
        if username.startswith('HS'):
            from hotspot import services
            mac = attrs.get('Calling-Station-Id', '')
            session_id = str(attrs.get('Acct-Session-Id', ''))
            if operation == 'authorize':
                return Response(radius_json(services.authorize(nas, username, mac, session_id)))
            if operation == 'commit':
                services.commit(nas, username, mac, session_id)
            elif operation == 'accounting':
                try:
                    services.account(nas, username, attrs)
                except (ValueError, TypeError):
                    raise ValidationError('Invalid accounting data.') from None
            else:
                raise PermissionDenied()
            return Response(status=204)
        from mikrotik.models import RouterInfo
        info = RouterInfo.objects.select_related('customer__organization').filter(
            pppoe_name=username, authentication_mode='radius', router_id=nas.router_id,
            customer__organization=nas.organization).first() if nas.router_id else None
        if not info:
            raise PermissionDenied('Subscriber does not belong to this NAS.')
        if operation == 'accounting':
            return Response(status=204)
        if info.customer.customer_status != 'active':
            raise PermissionDenied('Subscriber is suspended.')
        if operation == 'commit':
            return Response(status=204)
        if operation != 'authorize':
            raise PermissionDenied()
        if RadiusCheck.objects.filter(username=username, attribute='Auth-Type', value='Reject').exists():
            raise PermissionDenied()
        password = RadiusCheck.objects.filter(username=username, attribute='Cleartext-Password').values_list('value', flat=True).first()
        if password is None:
            raise PermissionDenied()
        result = {'control:Cleartext-Password': password}
        # Only expected plan attributes may cross the bridge.
        for row in RadiusReply.objects.filter(username=username, attribute__in=['Mikrotik-Rate-Limit', 'Session-Timeout', 'Acct-Interim-Interval']):
            result['reply:' + row.attribute] = row.value
        return Response(radius_json(result))
